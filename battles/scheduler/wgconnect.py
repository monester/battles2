import copy
from time import perf_counter
from datetime import datetime, time
import pytz
from itertools import groupby

from django.conf import settings

import wargaming
import logging
import requests
from requests.exceptions import RequestException

from .util import memcache
from .models import Clan


log = logging.getLogger(__name__)

wot = wargaming.WoT(settings.WARGAMING_API, 'ru', 'ru')
wgn = wargaming.WGN(settings.WARGAMING_API, 'ru', 'ru')

MEMCACHE_LIFETIME = 10


def log_time(func):
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        end = perf_counter()
        print(f'{func.__name__} used {end-start} seconds')
        return result
    return wrapper


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
def get_clan_data(clan_tag):
    clans = wgn.clans.list(search=clan_tag)
    for i in clans:
        if i['tag'] == clan_tag:
            return i


class WGClanBattles:
    """Collect all battles from different sources
    Clan can be listed in globalmap.provinces():
    - province['attackers'] or province['competitors']
    - province['active_battles']['clan_a'] or province['active_battles']['clan_b']
    - province['owner']
    Clan may be found only in GameAPI if it doesn't have opposite clan
    - game_api['planned_battles']['clan']
    """
    def __init__(self, clan_id, provinces_ids):
        self.clan_id = clan_id
        self._game_api_clan_battles = None
        self._wg_papi_provinces = None
        self._wg_papi_clan_provinces = None
        self.provinces_ids = provinces_ids

    @property
    @log_time
    def game_api_clan_battles(self):
        if self._game_api_clan_battles is not None:
            return self._game_api_clan_battles
        game_api_url = f'https://ru.wargaming.net/globalmap/game_api/clan/{self.clan_id}/battles'
        game_api_memcache = f'game_api/{self.clan_id}/battles'
        data = memcache.get(game_api_memcache)
        if data is None:
            try:
                data = requests.get(game_api_url)
            except RequestException:
                data = {}
            else:
                data = data.json()
                memcache.set(game_api_memcache, data, expire=MEMCACHE_LIFETIME)
        self._game_api_clan_battles = data
        return self._game_api_clan_battles

    @property
    @log_time
    def wg_papi_clan_provinces(self):
        """wot.globalmap.clanprovinces"""
        if self._wg_papi_clan_provinces is not None:
            return self._wg_papi_clan_provinces[str(self.clan_id)]
        self._wg_papi_clan_provinces = wot.globalmap.clanprovinces(clan_id=self.clan_id)
        return self._wg_papi_clan_provinces[str(self.clan_id)] or []

    @property
    @log_time
    def wg_papi_provinces(self):
        """wot.globalmap.clanprovinces"""
        if self._wg_papi_provinces is not None:
            return self._wg_papi_provinces
        provinces_data = []
        involved_provinces = self.get_involved_provinces()
        involved_provinces.update(self.provinces_ids)
        involved_provinces = sorted(involved_provinces)
        for front_id, provinces_ids in groupby(involved_provinces, lambda x: x[0]):
            province_id = list(i[1] for i in provinces_ids)
            provinces_data += list(wot.globalmap.provinces(
                front_id=front_id, province_id=province_id))
        self._wg_papi_provinces = provinces_data
        return provinces_data

    def get_involved_provinces(self):
        provinces_ids = set()

        # active battles in list
        for i in self.game_api_clan_battles['battles']:
            provinces_ids.add((i['front_id'], i['province_id']))

        # planned battles from unofficial api
        for i in self.game_api_clan_battles['planned_battles']:
            provinces_ids.add((i['front_id'], i['province_id']))

        for i in self.wg_papi_clan_provinces:
            provinces_ids.add((i['front_id'], i['province_id']))

        return provinces_ids

    @staticmethod
    @log_time
    def get_tournament_info(province_id):
        return requests.get(
            f'https://ru.wargaming.net/globalmap/game_api/tournament_info?alias={province_id}'
        ).json()

    def get_clan_battles_for_province(self, province_data):
        # battles can be found only in started provinces
        if province_data['status'] != 'STARTED':
            return []

        for battle in province_data['active_battles']:
            clan_a_id = battle['clan_a']['clan_id']
            clan_b_id = battle['clan_b']['clan_id']
            if self.clan_id in [clan_a_id, clan_b_id]:
                return [{
                    'round': battle['round'],
                    'start_at': battle['start_at'],
                    'clan_a': {'clan_id': clan_a_id},
                    'clan_b': {'clan_id': clan_b_id},
                }]

        # battle with owner hasn't started yet
        if self.clan_id == province_data['owner_clan_id']:
            return []

        print("HIT LONG: " + province_data['province_id'])

        # battle is missing in province battles. Maybe clan is skipping this round,
        # but this info is available only in tournament_info

        # wg_game api doesn't return full datetime for
        if len(province_data['active_battles']) > 0:
            fake_start_at = province_data['active_battles'][0]['start_at']
        else:
            fake_start_at = province_data['battles_start_at']

        tournament_info = self.get_tournament_info(province_data['province_id'])
        for battle in tournament_info['battles']:
            clan_a_id = battle['first_competitor'] and battle['first_competitor']['id']
            clan_b_id = battle['second_competitor'] and battle['second_competitor']['id']
            if self.clan_id in [clan_a_id, clan_b_id]:
                return [{
                    'round': tournament_info['round_number'],
                    'start_at': fake_start_at,
                    'clan_a': {'clan_id': clan_a_id},
                    'clan_b': {'clan_id': clan_b_id},
                }]

        # we didn't found clan in active battles?
        return []

    def get_clan_battles(self):
        provinces = []
        for province_data in self.wg_papi_provinces:
            battles = self.get_clan_battles_for_province(province_data)
            province = copy.deepcopy(province_data)
            province['battles_start_at'] = province['battles_start_at']
            province['active_battles'] = battles
            provinces.append(province)
        return normalize_provinces_data(provinces)
