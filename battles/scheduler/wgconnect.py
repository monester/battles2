from datetime import datetime, time
import pytz

from django.conf import settings

import wargaming
import logging
import requests
from requests.exceptions import RequestException

from .util import memcached, log_time, memcache


log = logging.getLogger(__name__)

wot = wargaming.WoT(settings.WARGAMING_API, 'ru', 'ru')
wgn = wargaming.WGN(settings.WARGAMING_API, 'ru', 'ru')


def convert_dt(date):
    return datetime.strptime(date, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.UTC)


def normalize_province_data(province):
    # convert battles_start_at from str to datetime
    province['battles_start_at'] = convert_dt(province['battles_start_at'])
    province['prime_time'] = time(*map(int, province['prime_time'].split(':')))

    # convert str to datetime for active battles
    for battle in province['active_battles']:
        battle['start_at'] = convert_dt(battle['start_at'])
    return province


def normalize_provinces_data(provinces):
    return [normalize_province_data(p)for p in provinces]


@log_time
@memcached()
def get_clan_data(clan_tag):
    try:
        clans = wgn.clans.list(search=clan_tag)
        for i in clans:
            if i['tag'] == clan_tag:
                return i
    except wargaming.exceptions.RequestError as e:
        log.error("Unable to find clan %s: %s", clan_tag, e.message)


@log_time
def get_clans_tags(clan_ids):
    try:
        return wgn.clans.info(clan_id=clan_ids, fields='tag').items()
    except wargaming.exceptions.RequestError as e:
        log.error(e.message)
    return {}


@log_time
@memcached()
def game_api_tournament_info(province_id):
    tournament_info_url = f'https://ru.wargaming.net/globalmap/game_api/' \
                          f'tournament_info?alias={province_id}'
    try:
        data = requests.get(tournament_info_url)
    except RequestException as e:
        log.error('Unable to get data from %s: %s', tournament_info_url, e)
        data = {
            'battles': [],
        }
    else:
        # TODO: add scheme validation
        data = data.json()
    return data


@log_time
@memcached()
def game_api_clan_battles(clan_id):
    game_api_url = f'https://ru.wargaming.net/globalmap/game_api/clan/{clan_id}/battles'
    try:
        data = requests.get(game_api_url)
    except RequestException as e:
        log.error('Unable to get data from %s: %s', game_api_url, e)
        data = {
            'battles': [],
            'planned_battles': []
        }
    else:
        # TODO: add scheme validation
        data = data.json()
    return data


@log_time
@memcached()
def wot_globalmap_clanprovinces(clan_id):
    return wot.globalmap.clanprovinces(clan_id=clan_id)


@log_time
@memcached(list_field='province_id')
def wot_globalmap_provinces(front_id, province_id):
    return {
        i['province_id']: i
        for i in wot.globalmap.provinces(front_id=front_id, province_id=province_id)
    }


class WGProvinceData:
    """Class representing all cumulative data for the province from WG API/Game API"""
    # [WGProvinceData, WGProvinceData, ...]
    _need_update = []

    def __init__(self, front_id, province_id):
        self.key = f'{front_id}/{province_id}'
        self.front_id = front_id
        self.province_id = province_id
        self._data = None

    @staticmethod
    def _fetch_api_provinces_data(grouped):
        """Get provinces data from WG Public API"""
        provinces_data = {}
        for front_id, province_id in grouped.items():
            raw_data = wot_globalmap_provinces(front_id=front_id, province_id=province_id)
            for province_data in raw_data.values():
                key = '{front_id}/{province_id}'.format(
                    front_id=province_data['front_id'],
                    province_id=province_data['province_id'])
                provinces_data[key] = province_data

                province_data['pretenders'] = \
                    province_data.pop('competitors') + province_data.pop('attackers')

                if len(province_data['pretenders']) == 0:
                    continue

                # check that battle in provinces has been started
                if province_data['status'] != 'STARTED':
                    continue

                # check that there is at least one battle.
                # if no battles in province with status 'STARTED' log this error
                if len(province_data['active_battles']) == 0:
                    print("ERROR: No battles in province %s with status 'STARTED'!")

                # collect all clans involved in battles
                clans_in_battles = set()
                for battle in province_data['active_battles']:
                    clans_in_battles.add(battle['clan_a']['clan_id'])
                    clans_in_battles.add(battle['clan_b']['clan_id'])

                # if there is only ONE clan without battle, then clan is skipping this round
                # add fake record
                skipping_clans = len(province_data['pretenders']) - len(clans_in_battles)
                if skipping_clans == 1:
                    battle_to_copy = province_data['active_battles'][0]
                    missing_clan = (set(province_data['pretenders']) - clans_in_battles).pop()
                    province_data['active_battles'].append({
                        'clan_a': {'clan_id': missing_clan},
                        'clan_b': {'clan_id': None},
                        'start_at': battle_to_copy['start_at'],
                        'round': battle_to_copy['round'],
                    })
                elif skipping_clans > 1:
                    print("ERROR: more than 1 clan is skipping battles on this province!")
        return provinces_data

    def _get_memcached(self):
        self._data = memcache.get(self.key)
        if not self._data:
            self.__class__._need_update.append(self)
        else:
            self._data = normalize_province_data(self.data)

    @staticmethod
    def _fetch_data_game_api(province_data):
        print(province_data)
        # reset data to avoid incorrect values
        province_data['active_battles'] = []
        tournament_info = game_api_tournament_info(province_data['province_id'])
        for battle in tournament_info['battles']:
            clan_a = {
                'clan_id': battle['first_competitor']['id']
            }
            clan_b = {
                'clan_id': None if battle['is_fake'] else battle['second_competitor']['id']
            }

            province_data['active_battles'].append({
                'clan_a': clan_a,
                'clan_b': clan_b,
                'round': tournament_info['round_number'],
                # FixMe: set start_at value from tournament_info
                'start_at': province_data['battles_start_at']
            })
        province_data['round_number'] = tournament_info['round_number']

    @classmethod
    def _update(cls):
        grouped = {}
        instances = {}

        # group provinces by fronts
        while True:
            try:
                # Avoiding possible race condition when 2 threads would tries
                # to update same cache.
                # pop() is atomic operation
                instance = cls._need_update.pop()
                front_id, province_id = instance.front_id, instance.province_id
            except IndexError:
                break
            grouped.setdefault(front_id, []).append(province_id)
            instances[f'{front_id}/{province_id}'] = instance
        cls._need_update = []

        # fetch data from PAPI
        provinces_data = cls._fetch_api_provinces_data(grouped)

        # validate data
        for province_data in provinces_data.values():
            active_battles = province_data['active_battles']
            owner_id = province_data['owner_clan_id']

            # check if there is only one battle with owner
            if all([
                owner_id is not None,
                len(active_battles) == 1,
                owner_id in [
                    active_battles[0]['clan_a']['clan_id'],
                    active_battles[0]['clan_b']['clan_id'],
                    ]
                ]):
                    continue

            if province_data['status'] == 'STARTED' and province_data['pretenders'] == []:
                # If no attackers clans in PAPI response then it is impossible to
                # detect if clan has no opponent because there is no such option in PAPI.
                # Using Unofficial WG API to get required data
                cls._fetch_data_game_api(province_data)

        # save it to memcache
        memcache.set_many(provinces_data, 300)

        # fill WGProvinceData instances with updated values
        for key, province_data in provinces_data.items():
            instances[key].data = normalize_province_data(province_data)

    @property
    def data(self):
        if self._data:
            return self._data
        self._get_memcached()
        if not self._data:
            self._update()
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def __getitem__(self, item):
        return self.data[item]

    # to make set(provinces_list) working correctly
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.key == other.key
        return self.data == other


class WGClanBattles:
    """Collect all battles from different sources
    Clan can be listed in globalmap.provinces():
    - province['attackers'] or province['competitors']
    - province['active_battles']['clan_a'] or province['active_battles']['clan_b']
    - province['owner']
    Clan may be found only in GameAPI if it doesn't have opposite clan
    - game_api['planned_battles']['clan']
    """
    def __init__(self, clan_id, provinces_ids=None):
        self.clan_id = clan_id
        self._game_api_clan_battles = None
        self._wg_papi_provinces = None
        self._wg_papi_clan_provinces = None
        self.provinces_ids = provinces_ids or []

    @property
    def game_api_clan_battles(self):
        if self._game_api_clan_battles is None:
            self._game_api_clan_battles = game_api_clan_battles(self.clan_id)
        return self._game_api_clan_battles

    @property
    def wg_papi_clan_provinces(self):
        """wot.globalmap.clanprovinces"""
        if self._wg_papi_clan_provinces is None:
            self._wg_papi_clan_provinces = \
                wot_globalmap_clanprovinces(self.clan_id)
        return self._wg_papi_clan_provinces[str(self.clan_id)] or []

    def list_involved_provinces(self):
        # planned battles from unofficial api and WG_PAPI
        all_battles = self.game_api_clan_battles['battles'] + \
            self.game_api_clan_battles['planned_battles'] + \
            self.wg_papi_clan_provinces

        # active battles in list
        return set(
            list((i['front_id'], i['province_id']) for i in all_battles) +
            list(self.provinces_ids)
        )

    def get_clan_related_provinces(self):
        provinces = []
        for front_id, province_id in self.list_involved_provinces():
            provinces.append(WGProvinceData(front_id, province_id))
        return provinces
