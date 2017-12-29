from unittest.mock import patch
from django.test import TestCase
from datetime import datetime, time
import pytz

from scheduler.wgconnect import WGClanBattles
from scheduler.wgconnect import wot_globalmap_provinces


class TestWGConnectWrappers(TestCase):
    def setUp(self):
        self.memcache = patch('scheduler.util.memcache')
        memcache = self.memcache.start()
        memcache.get.return_value = None
        memcache.get_many.return_value = {}

    def tearDown(self):
        self.memcache.stop()

    @patch('scheduler.wgconnect.wot')
    def test_wot_globalmap_provinces(self, wot):
        province_data = {
            'active_battles': [],
            'attackers': [],
            'competitors': [1, 2, 3, 4, 5, 6, 7],
            'front_id': 'front_id',
            'arena_id': 'arena_id',
            'arena_name': 'arena',
            'province_id': 'province_id',
            'province_name': 'province',
            'prime_time': '18:15',
            'battles_start_at': '2017-12-13T18:15:00',
            'round_number': 6,
            'owner_clan_id': 999,
            'status': 'FINISHED',
        }
        wot.globalmap.provinces.return_value = [province_data]
        assert wot_globalmap_provinces(front_id='fake', province_id=['fake']) == {
            'province_id': province_data
        }


class TestWGClanBattles(TestCase):
    def setUp(self):
        self.not_started_provinces = {
            'province_id': {
                'active_battles': [],
                'attackers': [],
                'competitors': [1, 2, 3, 4, 5, 6, 7],
                'front_id': 'front_id',
                'arena_id': 'arena_id',
                'arena_name': 'arena',
                'province_id': 'province_id',
                'province_name': 'province',
                'prime_time': '18:15',
                'battles_start_at': '2017-12-13T18:15:00',
                'round_number': 6,
                'owner_clan_id': 999,
                'status': 'FINISHED',
            }
        }

    @patch('scheduler.wgconnect.wot_globalmap_provinces')
    @patch('scheduler.wgconnect.game_api_clan_battles')
    @patch('scheduler.wgconnect.wot_globalmap_clanprovinces')
    def test_owned_province_not_started(self,
                                        wot_globalmap_clanprovinces,
                                        game_api_clan_battles,
                                        wot_globalmap_provinces):
        wot_globalmap_clanprovinces.return_value = {
            '1': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }]
        }
        game_api_clan_battles.return_value = {
            'battles': [],
            'planned_battles': [],
        }
        wot_globalmap_provinces.return_value = self.not_started_provinces
        assert WGClanBattles(1).get_clan_related_provinces() == [{
            'active_battles': [],
            'pretenders': [1, 2, 3, 4, 5, 6, 7],
            'front_id': 'front_id',
            'arena_id': 'arena_id',
            'arena_name': 'arena',
            'province_id': 'province_id',
            'province_name': 'province',
            'prime_time': time(18, 15),
            'battles_start_at': datetime(2017, 12, 13, 18, 15, 0, tzinfo=pytz.UTC),
            'round_number': 6,
            'owner_clan_id': 999,
            'status': 'FINISHED',
        }]

    @patch('scheduler.wgconnect.wot_globalmap_provinces')
    @patch('scheduler.wgconnect.game_api_clan_battles')
    @patch('scheduler.wgconnect.wot_globalmap_clanprovinces')
    def test_planned_province_not_started(
            self,
            wot_globalmap_clanprovinces,
            game_api_clan_battles,
            wot_globalmap_provinces
    ):
        wot_globalmap_clanprovinces.return_value = {
            '1': None
        }
        game_api_clan_battles.return_value = {
            'battles': [],
            'planned_battles': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }],
        }
        wot_globalmap_provinces.return_value = self.not_started_provinces
        assert WGClanBattles(1).get_clan_related_provinces() == [{
            'active_battles': [],
            'pretenders': [1, 2, 3, 4, 5, 6, 7],
            'front_id': 'front_id',
            'arena_id': 'arena_id',
            'arena_name': 'arena',
            'province_id': 'province_id',
            'province_name': 'province',
            'prime_time': time(18, 15),
            'battles_start_at': datetime(2017, 12, 13, 18, 15, 0, tzinfo=pytz.UTC),
            'round_number': 6,
            'owner_clan_id': 999,
            'status': 'FINISHED',
        }]

    @patch('scheduler.wgconnect.wot_globalmap_provinces')
    @patch('scheduler.wgconnect.game_api_clan_battles')
    @patch('scheduler.wgconnect.wot_globalmap_clanprovinces')
    def test_planned_province_started_with_pretenders_province_round_1(
            self,
            wot_globalmap_clanprovinces,
            game_api_clan_battles,
            wot_globalmap_provinces
    ):
        wot_globalmap_clanprovinces.return_value = {
            '1': None
        }
        game_api_clan_battles.return_value = {
            'battles': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }],
            'planned_battles': [],
        }
        wot_globalmap_provinces.return_value = {
            'province_id': {
                'active_battles': [{
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 1},
                    'clan_b': {'clan_id': 2},
                    'round': 1,
                }, {
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 3},
                    'clan_b': {'clan_id': 4},
                    'round': 1,
                }, {
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 5},
                    'clan_b': {'clan_id': 6},
                    'round': 1,
                }],
                'attackers': [],
                'competitors': [1, 2, 3, 4, 5, 6],
                'front_id': 'front_id',
                'arena_id': 'arena_id',
                'arena_name': 'arena',
                'province_id': 'province_id',
                'province_name': 'province',
                'prime_time': '18:15',
                'battles_start_at': '2017-12-13T18:15:00',
                'round_number': 1,
                'owner_clan_id': 999,
                'status': 'STARTED',
            }
        }
        assert WGClanBattles(1).get_clan_related_provinces()[0]['active_battles'] == [{
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 1},
            'clan_b': {'clan_id': 2},
            'round': 1,
        }, {
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 3},
            'clan_b': {'clan_id': 4},
            'round': 1,
        }, {
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 5},
            'clan_b': {'clan_id': 6},
            'round': 1,
        }]

    @patch('scheduler.wgconnect.wot_globalmap_provinces')
    @patch('scheduler.wgconnect.game_api_clan_battles')
    @patch('scheduler.wgconnect.wot_globalmap_clanprovinces')
    def test_planned_province_started_with_pretenders_no_opponent_province_round_1(
            self,
            wot_globalmap_clanprovinces,
            game_api_clan_battles,
            wot_globalmap_provinces
    ):
        wot_globalmap_clanprovinces.return_value = {
            '1': None
        }
        game_api_clan_battles.return_value = {
            'battles': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }],
            'planned_battles': [],
        }
        wot_globalmap_provinces.return_value = {
            'province_id': {
                'active_battles': [{
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 1},
                    'clan_b': {'clan_id': 2},
                    'round': 1,
                }, {
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 3},
                    'clan_b': {'clan_id': 4},
                    'round': 1,
                }],
                'attackers': [],
                'competitors': [1, 2, 3, 4, 5],
                'front_id': 'front_id',
                'arena_id': 'arena_id',
                'arena_name': 'arena',
                'province_id': 'province_id',
                'province_name': 'province',
                'prime_time': '18:15',
                'battles_start_at': '2017-12-13T18:15:00',
                'round_number': 1,
                'owner_clan_id': 999,
                'status': 'STARTED',
            }
        }
        assert WGClanBattles(1).get_clan_related_provinces()[0]['active_battles'] == [{
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 1},
            'clan_b': {'clan_id': 2},
            'round': 1,
        }, {
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 3},
            'clan_b': {'clan_id': 4},
            'round': 1,
        }, {
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 5},
            'clan_b': {'clan_id': None},
            'round': 1,
        }]

    @patch('scheduler.wgconnect.wot_globalmap_provinces')
    @patch('scheduler.wgconnect.game_api_clan_battles')
    @patch('scheduler.wgconnect.wot_globalmap_clanprovinces')
    @patch('scheduler.wgconnect.game_api_tournament_info')
    def test_planned_province_started_no_pretenders_round_1(
            self,
            game_api_tournament_info,
            wot_globalmap_clanprovinces,
            game_api_clan_battles,
            wot_globalmap_provinces
    ):
        wot_globalmap_clanprovinces.return_value = {
            '1': None
        }
        game_api_clan_battles.return_value = {
            'battles': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }],
            'planned_battles': [],
        }
        wot_globalmap_provinces.return_value = {
            'province_id': {
                'active_battles': [{
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 1},
                    'clan_b': {'clan_id': 2},
                    'round': 1,
                }, {
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 3},
                    'clan_b': {'clan_id': 4},
                    'round': 1,
                }],
                'attackers': [],
                'competitors': [],
                'front_id': 'front_id',
                'arena_id': 'arena_id',
                'arena_name': 'arena',
                'province_id': 'province_id',
                'province_name': 'province',
                'prime_time': '18:15',
                'battles_start_at': '2017-12-13T18:15:00',
                'round_number': 1,
                'owner_clan_id': 999,
                'status': 'STARTED',
            }
        }
        game_api_tournament_info.return_value = {
            'round_number': 1,
            'battles': [{
                'first_competitor': {'id': 1},
                'second_competitor': {'id': 2},
            }, {
                'first_competitor': {'id': 3},
                'second_competitor': {'id': 4},
            },{
                'first_competitor': {'id': 5},
                'second_competitor': None,
            }]
        }
        assert WGClanBattles(1).get_clan_related_provinces()[0]['active_battles'] == [{
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 1},
            'clan_b': {'clan_id': 2},
            'round': 1,
        }, {
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 3},
            'clan_b': {'clan_id': 4},
            'round': 1,
        }, {
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 5},
            'clan_b': {'clan_id': None},
            'round': 1,
        }]

    @patch('scheduler.wgconnect.wot_globalmap_provinces')
    @patch('scheduler.wgconnect.game_api_clan_battles')
    @patch('scheduler.wgconnect.wot_globalmap_clanprovinces')
    @patch('scheduler.wgconnect.game_api_tournament_info')
    def test_planned_province_started_no_pretenders_round_owner(
            self,
            game_api_tournament_info,
            wot_globalmap_clanprovinces,
            game_api_clan_battles,
            wot_globalmap_provinces
    ):
        wot_globalmap_clanprovinces.return_value = {
            '1': None
        }
        game_api_clan_battles.return_value = {
            'battles': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }],
            'planned_battles': [],
        }
        wot_globalmap_provinces.return_value = {
            'province_id': {
                'active_battles': [{
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 1},
                    'clan_b': {'clan_id': 2},
                    'round': 1,
                }],
                'attackers': [],
                'competitors': [],
                'front_id': 'front_id',
                'arena_id': 'arena_id',
                'arena_name': 'arena',
                'province_id': 'province_id',
                'province_name': 'province',
                'prime_time': '18:15',
                'battles_start_at': '2017-12-13T18:15:00',
                'round_number': 1,
                'owner_clan_id': 2,
                'status': 'STARTED',
            }
        }
        game_api_tournament_info.side_effect = Exception("Should not be run")
        assert WGClanBattles(1).get_clan_related_provinces()[0]['active_battles'] == [{
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 1},
            'clan_b': {'clan_id': 2},
            'round': 1,
        }]

    @patch('scheduler.wgconnect.wot_globalmap_provinces')
    @patch('scheduler.wgconnect.game_api_clan_battles')
    @patch('scheduler.wgconnect.wot_globalmap_clanprovinces')
    @patch('scheduler.wgconnect.game_api_tournament_info')
    def test_planned_province_started_with_pretenders_round_owner(
            self,
            game_api_tournament_info,
            wot_globalmap_clanprovinces,
            game_api_clan_battles,
            wot_globalmap_provinces
    ):
        wot_globalmap_clanprovinces.return_value = {
            '1': None
        }
        game_api_clan_battles.return_value = {
            'battles': [{
                'front_id': 'front_id',
                'province_id': 'province_id',
            }],
            'planned_battles': [],
        }
        wot_globalmap_provinces.return_value = {
            'province_id': {
                'active_battles': [{
                    'start_at': '2017-12-13T18:15:00',
                    'clan_a': {'clan_id': 1},
                    'clan_b': {'clan_id': 2},
                    'round': 1,
                }],
                'attackers': [1],
                'competitors': [],
                'front_id': 'front_id',
                'arena_id': 'arena_id',
                'arena_name': 'arena',
                'province_id': 'province_id',
                'province_name': 'province',
                'prime_time': '18:15',
                'battles_start_at': '2017-12-13T18:15:00',
                'round_number': 1,
                'owner_clan_id': 2,
                'status': 'STARTED',
            }
        }
        game_api_tournament_info.side_effect = Exception("Should not be run")
        assert WGClanBattles(1).get_clan_related_provinces()[0]['active_battles'] == [{
            'start_at': datetime(2017, 12, 13, 18, 15, tzinfo=pytz.UTC),
            'clan_a': {'clan_id': 1},
            'clan_b': {'clan_id': 2},
            'round': 1,
        }]
