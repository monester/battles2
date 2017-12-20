from time import perf_counter
from itertools import chain, groupby
from datetime import datetime, timedelta, time
import pytz

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


@log_time
def get_provinces_data(clan_provinces):
    # --- Gather info about provinces via WG PAPI ---
    provinces = []
    clan_provinces = sorted(clan_provinces, key=lambda x: x['front_id'])
    for front_id, province_ids in groupby(clan_provinces, lambda x: x['front_id']):
        # extract ids from data
        provinces_ids = [x['province_id'] for x in province_ids]

        # get data from memcache
        cache_keys = [f'{front_id}/{province_id}' for province_id in provinces_ids]
        cached_data = memcache.get_many(cache_keys)
        provinces.extend(cached_data.values())

        # get miss cache
        missed_ids = [
            province_id for province_id in provinces_ids
            if f'{front_id}/{province_id}' not in cached_data
        ]
        if missed_ids:
            log.debug(f"Missed following provinces: {missed_ids} on {front_id}")
            provinces_data = wot.globalmap.provinces(front_id=front_id, province_id=provinces_ids)
            memcache.set_many({
                f'{front_id}/{province_data["province_id"]}': province_data
                for province_data in provinces_data
            }, expire=MEMCACHE_LIFETIME)
            provinces.extend(provinces_data)

    # Normalize data
    for province in provinces:
        # convert battles_start_at from str to datetime
        province['battles_start_at'] = convert_dt(province['battles_start_at'])
        province['prime_time'] = time(*map(int, province['prime_time'].split(':')))

        # convert clan_ids to the Clan instances
        province['competitors'] = [
            Clan.objects.get_or_create(id=clan_id)[0]
            for clan_id in province['competitors']
        ]
        province['attackers'] = [
            Clan.objects.get_or_create(id=clan_id)[0]
            for clan_id in province['attackers']
        ]

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
        clan_provinces = wot.globalmap.clanprovinces(clan_id=clan_id)[str(clan_id)] or []
        memcache.set(clan_provinces_memcache, clan_provinces, expire=MEMCACHE_LIFETIME)

    # get clan engaged attacks from GAME API
    game_api_url = f'https://ru.wargaming.net/globalmap/game_api/clan/{clan_id}/battles'
    game_api_memcache = f'game_api/{clan_id}/battles'
    data = memcache.get(game_api_memcache)
    if not data:
        try:
            data = requests.get(game_api_url)
        except RequestException as e:
            data = []
        else:
            data = data.json()
            memcache.set(game_api_memcache, data, expire=MEMCACHE_LIFETIME)
            clan_provinces.extend(data['planned_battles'])
            clan_provinces.extend(data['battles'])

    return clan_provinces


@log_time
def get_clan_data(clan_tag):
    clans = wgn.clans.list(search=clan_tag)
    for i in clans:
        if i['tag'] == clan_tag:
            return i
