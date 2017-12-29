import requests
from unittest.mock import patch
from django.test import TestCase

from scheduler.wgconnect import get_clan_related_provinces

from scheduler.models import Clan, Schedule, ProvinceBattles
from scheduler.views import FetchClanDataView


class TestImport(TestCase):
    def setUp(self):
        self.owner_clan_id = '1'
        self.clan_provinces = {
            self.owner_clan_id: [{
                'front_id': 'front_id',
                'province_id': 'province_id_1',
            }, {
                'front_id': 'front_id',
                'province_id': 'province_id_2',
            }]
        }

        self.provinces_data = [{
            'active_battles': [],
            'attackers': [],
            'competitors': [1, 2, 3, 4, 5, 6, 7],
            'front_id': 'front1',
            'arena_id': 'map1',
            'arena_name': 'map1',
            'province_id': 'province_id_3',
            'province_name': 'province_3',
            'prime_time': '18:15',
            'battles_start_at': '2017-12-13T18:15:00',
            'round_number': 6,
            'owner_clan_id': 999,
            'status': 'FINISHED',
        }, {
            'active_battles': [{
                'clan_a': {'clan_id': 1},
                'clan_b': {'clan_id': 2},
                'round': 1,
                'start_at': '2017-12-16T17:15:10',
            }, {
                'clan_a': {'clan_id': 3},
                'clan_b': {'clan_id': 4},
                'round': 1,
                'start_at': '2017-12-16T17:15:10',
            }, {
                'clan_a': {'clan_id': 5},
                'clan_b': {'clan_id': 6},
                'round': 1,
                'start_at': '2017-12-16T17:15:10',
            }],
            'attackers': [],
            'competitors': [1, 2, 3, 4, 5, 6],
            'battles_start_at': '2017-12-16T17:15:10',
            'front_id': 'front1',
            'arena_id': 'map1',
            'arena_name': 'map1',
            'province_id': 'province2',
            'province_name': 'province2_name',
            'prime_time': '17:15',
            'round_number': 1,
            'owner_clan_id': 999,
            'status': 'STARTED',
        }, {
            'active_battles': [{
                'clan_a': {'clan_id': 1},
                'clan_b': {'clan_id': 2},
                'round': 2,
                'start_at': '2017-12-16T17:15:10',
            }, {
                'clan_a': {'clan_id': 3},
                'clan_b': {'clan_id': 4},
                'round': 2,
                'start_at': '2017-12-16T17:15:10',
            }, {
                'clan_a': {'clan_id': 5},
                'clan_b': {'clan_id': 6},
                'round': 2,
                'start_at': '2017-12-16T17:15:10',
            }],
            'attackers': [],
            'competitors': [1, 2, 3, 4, 5, 6],
            'battles_start_at': '2017-12-16T17:15:10',
            'front_id': 'front1',
            'arena_id': 'map1',
            'arena_name': 'map1',
            'province_id': 'province3',
            'province_name': 'province3_name',
            'prime_time': '17:15',
            'round_number': 2,
            'owner_clan_id': 999,
            'status': 'STARTED',
        }]

    @patch('scheduler.wgconnect.requests')
    @patch('scheduler.wgconnect.wot')
    def not_started_schedule(self, wot, requests_mock):
        requests_mock.get.side_effect = requests.exceptions.RequestException()
        wot.globalmap.clanprovinces.return_value = self.clan_provinces
        wot.globalmap.provinces.return_value = self.provinces_data
        FetchClanDataView().update(clan_id='1')
        assert Province.objects.count() == 3
        assert Schedule.objects.count() == 3
        # assert Clan.objects.count() == 3
        province = Province.objects.get(province_id='province2')
        assert Schedule.objects.get(date='2017-12-16', province=province).battles.count() == 3


    def get_info_missing_end(self):
        # update  -> s attackers: clan, battles_starts_at: today
        # no update
        # next update -> attackers: [], battles_starts_at: tomorrow
        from .wgconnect import normalize_provinces_data
        first_fetch = {
            'active_battles': [],
            'attackers': [],
            'competitors': [1, 2, 3, 4, 5, 6, 7],
            'front_id': 'front1',
            'arena_id': 'map1',
            'arena_name': 'map1',
            'province_id': 'province1',
            'province_name': 'province1_name',
            'prime_time': '18:15',
            'battles_start_at': '2017-12-13T18:15:00',
            'round_number': 6,
            'owner_clan_id': 999,
            'status': 'FINISHED',
        }
        FetchClanDataView.update_province(normalize_provinces_data([first_fetch])[0])
        s = Schedule.objects.get(province__province_id='province1', date='2017-12-13')
        print(s.status)
        print(s.competitors.all())
        assert 1 == 0

        last_fetch = {
            'active_battles': [],
            'attackers': [],
            'competitors': [],
            'front_id': 'front1',
            'arena_id': 'map1',
            'arena_name': 'map1',
            'province_id': 'province1',
            'province_name': 'province1_name',
            'prime_time': '18:15',
            'battles_start_at': '2017-12-14T18:15:00',
            'round_number': 6,
            'owner_clan_id': 999,
            'status': 'FINISHED',
        }


class TestGetProvincesData(TestCase):
    @patch("scheduler.wgconnect.memcache")
    @patch('scheduler.wgconnect.wot')
    def test_get_all_from_memcache(self, wot, memcache):
        province_data = {
            'active_battles': [],
            'attackers': [],
            'competitors': [1, 2, 3, 4, 5, 6, 7],
            'front_id': 'front_id',
            'arena_id': 'map1',
            'arena_name': 'map1',
            'province_id': 'province_id',
            'province_name': 'province1_name',
            'prime_time': '18:15',
            'battles_start_at': '2017-12-13T18:15:00',
            'round_number': 6,
            'owner_clan_id': 999,
            'status': 'FINISHED',
        }
        memcache.get_many.return_value = {
            'front_id/province_id': province_data
        }
        # get_provinces_data({'front_id': ['province_id']})



class TestGetClanRelatedProvinces(TestCase):
    @patch('scheduler.wgconnect.memcache')
    @patch('scheduler.wgconnect.requests')
    @patch('scheduler.wgconnect.wot')
    def test_get_all_related_from_game_api(self, wot, requests, memcache):
        memcache.get.return_value = None
        memcache.get_many.return_value = None

        # https://ru.wargaming.net/globalmap/game_api/clan/{clan_id}/battles
        requests.get.return_value.json.return_value = {
           'battles': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }],
            'planned_battles': [],
        }
        wot.globalmap.clanprovinces.return_value = {'1': None}
        wot.globalmap.clanbattles = []

        assert get_clan_related_provinces(1) == {
            'front_id': ['province_id']
        }

    # def test_get_all_related_from_game_api(self, wot, requests, memcache):


