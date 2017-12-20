from unittest.mock import patch
from datetime import datetime, time
import pytz

import requests

from django.test import TestCase

from scheduler.models import Clan, Province, Schedule, ProvinceBalltes


# Create your tests here.
class TestSchedulerAttack(TestCase):
    def setUp(self):
        clan1, clan2, clan3, clan4, clan5, owner = [
            Clan.objects.create(tag='CLAN1'),
            Clan.objects.create(tag='CLAN2'),
            Clan.objects.create(tag='CLAN3'),
            Clan.objects.create(tag='CLAN4'),
            Clan.objects.create(tag='CLAN5'),
            Clan.objects.create(tag='OWNER'),
        ]
        province = Province.objects.create(province_id='province_id1', province_name='Province', prime_time='17:00')
        schedule = Schedule.objects.create(
            date='2017-01-01', battles_start_at='2017-01-01T17:00:00+00', province=province,
            owner=owner, is_landing=False, status='STARTED', round_number=2)
        schedule.attackers.set([clan1, clan2, clan3])
        self.schedule_started_id = schedule.id

        province = Province.objects.create(province_id='province_id2', province_name='Province', prime_time='18:00')
        schedule = Schedule.objects.create(
            date='2017-01-01', battles_start_at='2017-01-01T17:00:00+00', province=province,
            owner=owner, is_landing=False, status=None, round_number=None)
        schedule.attackers.set([clan1, clan2, clan3, clan4, clan5])
        self.schedule_not_started_id = schedule.id
        # create province, clans and schedule

    def test_correct_balltle_times_not_started(self):
        # round 2 : clan1 vs clan2 || clan1 vs clan3 || clan2 vs clan3 ||
        # round 2 : clan1 vs clan2 || clan1 vs clan3 || clan2 vs clan3
        # round 3 : clan1 vs clan3
        # final   : clan3 vs owner
        schedule = Schedule.objects.get(pk=self.schedule_not_started_id)
        clan = Clan.objects.get(tag='CLAN1')
        # assert schedule.owner is not None
        assert schedule.get_battle_times(clan) == {
            'attackers': [1, 2, 3, 4, 5],
            'mode': 'By Land',
            'owner': 6,
            'prime_time': time(18, 0),
            'province_id': 'province_id2',
            'province_name': 'Province',
            'rounds': [{
                'time': datetime.combine(schedule.date, time(18, 0)).replace(tzinfo=pytz.UTC),
                'title': '1/4',
                'clan_a': None,
                'clan_b': None,
            }, {
                'time': datetime.combine(schedule.date, time(18, 30)).replace(tzinfo=pytz.UTC),
                'title': '1/2',
                'clan_a': None,
                'clan_b': None,
            }, {
                'time': datetime.combine(schedule.date, time(19, 0)).replace(tzinfo=pytz.UTC),
                'title': 'Final',
                'clan_a': None,
                'clan_b': None,
            }, {
                'time': datetime.combine(schedule.date, time(19, 30)).replace(tzinfo=pytz.UTC),
                'title': 'Owner',
                'clan_a': schedule.owner,
                'clan_b': None,
            }],
        }

    def test_correct_balltle_times_started(self):
        pass

    def test_correct_balltle_times_with_draw_round(self):
        pass

    def test_correct_battle_opponents(self):
        # assert self.schedule.get_battle_opponents(clan1) == {
        #     "times": ["18:00", "18:30", "19:00"]
        # }
        pass


class TestSchedulerDefence(TestCase):
    def setUp(self):
        clan1, clan2, clan3, clan4, clan5, owner = [
            Clan.objects.create(tag='CLAN1'),
            Clan.objects.create(tag='CLAN2'),
            Clan.objects.create(tag='CLAN3'),
            Clan.objects.create(tag='CLAN4'),
            Clan.objects.create(tag='CLAN5'),
            Clan.objects.create(tag='OWNER'),
        ]
        date = '2017-01-01'
        province = Province.objects.create(province_id='province_id1', province_name='Province', prime_time='17:00')
        schedule = Schedule.objects.create(
            date=date, battles_start_at='2017-01-01T17:30:00+00', province=province,
            owner=owner, is_landing=False, status='STARTED', round_number=2)
        schedule.battles.bulk_create([
            ProvinceBalltes(schedule=schedule, clan_a=clan1, clan_b=clan2, start_at='2017-01-01T17:00:00+00', round=1),
            ProvinceBalltes(schedule=schedule, clan_a=clan3, clan_b=clan4, start_at='2017-01-01T17:00:00+00', round=1),
        ])
        schedule.attackers.set([clan1, clan3, clan5])
        self.schedule_started_id = schedule.id

    def test_correct_balltle_times_started(self):
        schedule = Schedule.objects.get(pk=self.schedule_started_id)
        clan = Clan.objects.get(tag='OWNER')
        assert schedule.get_battle_times(clan) == {
            # r1: 17-00: 1v2 3v4 5
            # r2: 17-30: 1v5 3
            # r3: 18-00: 1v3
            # r4: 18-30: 1vO
            'attackers': [1, 3, 5],
            'mode': 'Defence',
            'owner': 6,
            'prime_time': time(17, 0),
            'province_id': 'province_id1',
            'province_name': 'Province',
            'rounds': [{
                'time': datetime.combine(schedule.date, time(18, 30)).replace(tzinfo=pytz.UTC),
                'title': 'Owner',
                'clan_a': schedule.owner,
                'clan_b': None,
            }],
        }


from scheduler.views import FetchClanDataView
class TestImport(TestCase):
    def setUp(self):
        self.owner_clan_id = '1'
        self.clan_provinces = {
            self.owner_clan_id: [{
                'front_id': 'front1',
                'province_id': 'magnitka',
            }, {
                'front_id': 'front1',
                'province_id': 'sarana',
            }]
        }

        self.provinces_data = [{
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
    def test_not_started_schedule(self, wot, requests_mock):

        requests_mock.get.side_effect = requests.exceptions.RequestException()

        wot.globalmap.clanprovinces.return_value = self.clan_provinces
        wot.globalmap.provinces.return_value = self.provinces_data
        FetchClanDataView().update(clan_id='1')
        assert Province.objects.count() == 3
        assert Schedule.objects.count() == 3
        # assert Clan.objects.count() == 3
        province = Province.objects.get(province_id='province2')
        assert Schedule.objects.get(date='2017-12-16', province=province).battles.count() == 3
