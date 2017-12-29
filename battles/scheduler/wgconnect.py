import copy
from datetime import datetime, time
import pytz
from itertools import chain

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


def normalize_provinces_data(provinces):
    for province in provinces:
        # convert battles_start_at from str to datetime
        province['battles_start_at'] = convert_dt(province['battles_start_at'])
        province['prime_time'] = time(*map(int, province['prime_time'].split(':')))

        # convert str to datetime for active battles
        for battle in province['active_battles']:
            battle['start_at'] = convert_dt(battle['start_at'])
    return provinces


@log_time
@memcached()
def get_clan_related_provinces(clan_id=208182):
    # --- Get clan related provinces ---
    # get clan owned provinces from PAPI
    clan_provinces_memcache = f'globalmap.clanprovinces.{clan_id}'
    clan_provinces = memcache.get(clan_provinces_memcache)
    if clan_provinces is None:
        print (wot.globalmap.clanprovinces(clan_id=clan_id))
        clan_provinces = wot.globalmap.clanprovinces(clan_id=clan_id)[str(clan_id)] or []
        memcache.set(clan_provinces_memcache, clan_provinces, expire=MEMCACHE_LIFETIME)

    # get clan attacks from GAME API
    game_api_url = f'https://ru.wargaming.net/globalmap/game_api/clan/{clan_id}/battles'
    game_api_memcache = f'game_api/{clan_id}/battles'
    data = memcache.get(game_api_memcache)
    if data is None:
        try:
            data = requests.get(game_api_url)
        except RequestException as e:
            data = {}
        else:
            data = data.json()
            memcache.set(game_api_memcache, data, expire=MEMCACHE_LIFETIME)

    if data:
        clan_provinces.extend(data['planned_battles'])
        clan_provinces.extend(data['battles'])

    result = {}
    for p in clan_provinces:
        result.setdefault(p['front_id'], []).append(p['province_id'])
    return result


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
@memcached()
def game_api_tournament_info(province_id):
    return requests.get(
        f'https://ru.wargaming.net/globalmap/game_api/tournament_info?alias={province_id}'
    ).json()


@log_time
@memcached()
def game_api_clan_battles(clan_id):
    game_api_url = f'https://ru.wargaming.net/globalmap/game_api/clan/{clan_id}/battles'
    try:
        data = requests.get(game_api_url)
    except RequestException:
        data = {}
    else:
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


def get_battles_on_province(province_data):
    """Return all battles ongoing in province"""
    # battles can be found only in started provinces
    if province_data['status'] != 'STARTED':
        return []

    battles = []
    pretenders = set(province_data['competitors'] + province_data['attackers'])
    clans = set()

    for battle in province_data['active_battles']:
        clan_a_id = battle['clan_a']['clan_id']
        clan_b_id = battle['clan_b']['clan_id']
        clans.update(clan_a_id, clan_b_id)
        battles.append({
            'round': battle['round'],
            'start_at': battle['start_at'],
            'clan_a': {'clan_id': clan_a_id},
            'clan_b': {'clan_id': clan_b_id},
        })

    # [1,2,3]   = 1v2     => 3 >= 2
    # [1,2,3,4] = 1v2 3v4 => 4 >= 4
    # []        = 1v2     => 0 >= 2 !!!
    if len(pretenders) == len(clans):
        # all clans have battles in current round
        return battles
    elif len(pretenders) == len(clans) + 1:
        # some clan skipped it's round
        # fake battle should be generated
        battles.append({
            'round': province_data['round_number'],
            'start_at': province_data['battles_start_at'],
            'clan_a': {'clan_id': (pretenders - clans).pop()},
            'clan_b': {'clan_id': None},
        })
        return battles

    # WG_PAPI didn't return correct values in wot.globalmap.province method
    # possibly there is no clans in province_data['attackers'] or province_data['competitors']
    # so getting info about attacking clans from globalmap.
    # IT IS THE ONLY WAY TO DETECT IF CLAN IS SKIPPING ROUND BECAUSE OF NO OPPONENT

    print("HIT LONG: " + province_data['province_id'])

    if len(province_data['active_battles']) > 0:
        fake_start_at = province_data['active_battles'][0]['start_at']
    else:
        fake_start_at = province_data['battles_start_at']

    tournament_info = game_api_tournament_info(province_data['province_id'])
    battles = []
    for battle in tournament_info['battles']:
        clan_a_id = battle['first_competitor'] and battle['first_competitor']['id']
        clan_b_id = battle['second_competitor'] and battle['second_competitor']['id']
        battles.append({
            'round': tournament_info['round_number'],
            'start_at': fake_start_at,
            'clan_a': {'clan_id': clan_a_id},
            'clan_b': {'clan_id': clan_b_id},
        })
    return battles


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

    @property
    def wg_papi_provinces(self):
        """wot.globalmap.clanprovinces"""
        if self._wg_papi_provinces is not None:
            return self._wg_papi_provinces

        involved_provinces = {}
        for front_id, province_id in self.list_involved_provinces():
            involved_provinces.setdefault(front_id, set()).add(province_id)

        provinces_data = []
        for front_id, provinces_ids in involved_provinces.items():
            data = wot_globalmap_provinces(
                front_id=front_id,
                province_id=provinces_ids
            )
            for province_data in data.values():
                province_data['pretenders'] = province_data.pop('attackers') + \
                                              province_data.pop('competitors')
                provinces_data.append(province_data)
        self._wg_papi_provinces = provinces_data
        return provinces_data

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
        for province_data in self.wg_papi_provinces:
            battles = get_battles_on_province(province_data)
            province = copy.deepcopy(province_data)
            province['active_battles'] = battles
            provinces.append(province)
        return normalize_provinces_data(provinces)
