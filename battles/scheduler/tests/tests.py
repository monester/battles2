from unittest.mock import patch
from itertools import zip_longest
from datetime import datetime, time, timedelta
import pytz

import requests

from django.test import TestCase

from scheduler.models import Clan, Schedule, ProvinceBattles


def create_clans(number, owner=False):
    clans = []
    for i in range(1, number + 1):
        clans.append(Clan.objects.create(id=i, tag=f'CLAN{i}'))
    if owner:
        clans.append(Clan.objects.create(id=number + 1, tag=f'OWNER'))
    return clans

# def generate_game_api_tournament_info(**kwargs):
#     clans = kwargs.get('clans', [])
#     battles = []
#     for clan_a_id, clan_b_id in zip_longest(clans[::2], clans[1::2]):
#         first_competitor = {
#             'tag': f'tag{clan_a_id}',
#             'id': clan_a_id
#         }
#         second_competitor = clan_b_id and {
#             'tag': f'tag{clan_a_id}',
#             'id': clan_a_id
#         }
#         battles.append({
#             'first_competitor': first_competitor,
#             'second_competitor': second_competitor,
#             'is_fake': second_competitor is None,
#         })
#     owner = kwargs.get('owner', None)
#     owner = owner and {
#         'tag': f'tag{owner}',
#         'id': owner
#     }
#     return {
#         'owner': owner,
#         'battles': battles,
#         'province_id': kwargs.get('province_id', 'province_id'),
#         'round_number': kwargs.get('round_number', 1),
#     }
#
#
# # Create your tests here.

class TestBattleTimes(TestCase):
    def setUp(self):
        self.clan1, self.clan2, self.clan3, self.clan4, self.clan5, self.owner = \
            create_clans(5, owner=True)
        Schedule.objects.create(
            front_id='front_id',
            front_name='front',
            province_id='province_id',
            province_name='province',
            arena_id='arena_id',
            arena_name='arena',
            server='server',
            date='2017-01-01',
            prime_time='12:00',
            battles_start_at='2017-01-01T12:00:00Z',
            owner=self.owner,
        )

    def test_correct_fields_and_no_pretenders(self):
        schedule = Schedule.objects.first()
        assert schedule.get_battle_times(self.owner) == {
            'arena_name': 'arena',
            'mode': 'Defence',
            'owner': 6,
            'prime_time': time(12, 0),
            'province_id': 'province_id',
            'province_name': 'province',
            'server': 'server',
            'rounds': [],
        }

    def test_not_started_only_one_pretender(self):
        schedule = Schedule.objects.first()
        schedule.pretenders.add(self.clan1)
        assert schedule.get_battle_times(self.clan1)['rounds'] == [{
            'time': datetime.combine(schedule.date, time(12, 00)).replace(tzinfo=pytz.UTC),
            'title': 'Owner',
            'clan_a': schedule.owner,
            'clan_b': None,
            'start_at': None,
        }]

    def test_not_started_correct_battle_times(self):
        schedule = Schedule.objects.first()
        schedule.pretenders.add(self.clan1, self.clan2, self.clan3, self.clan4, self.clan5)
        assert schedule.get_battle_times(self.clan1)['rounds'] == [{
            'time': datetime.combine(schedule.date, time(12, 0)).replace(tzinfo=pytz.UTC),
            'title': '1/4',
            'clan_a': None,
            'clan_b': None,
            'start_at': None,
        }, {
            'time': datetime.combine(schedule.date, time(12, 30)).replace(tzinfo=pytz.UTC),
            'title': '1/2',
            'clan_a': None,
            'clan_b': None,
            'start_at': None,
        }, {
            'time': datetime.combine(schedule.date, time(13, 0)).replace(tzinfo=pytz.UTC),
            'title': 'Final',
            'clan_a': None,
            'clan_b': None,
            'start_at': None,
        }, {
            'time': datetime.combine(schedule.date, time(13, 30)).replace(tzinfo=pytz.UTC),
            'title': 'Owner',
            'clan_a': schedule.owner,
            'clan_b': None,
            'start_at': None,
        }]

    def test_not_started_owner(self):
        schedule = Schedule.objects.first()
        schedule.pretenders.add(self.clan1, self.clan2, self.clan3, self.clan4, self.clan5)
        assert schedule.get_battle_times(self.owner)['rounds'] == [{
            'time': datetime.combine(schedule.date, time(13, 30)).replace(tzinfo=pytz.UTC),
            'title': 'Owner',
            'clan_a': schedule.owner,
            'clan_b': None,
            'start_at': None,
        }]

    def test_started_only_one_pretender(self):
        schedule = Schedule.objects.first()
        schedule.round_number = 1
        schedule.save()
        schedule.battles.create(
            clan_a=self.clan1,
            clan_b=self.owner,
            round=1,
            start_at=datetime.combine(schedule.date, schedule.prime_time).replace(tzinfo=pytz.UTC)
        )
        start_at = datetime.combine(schedule.date, time(12, 00)).replace(tzinfo=pytz.UTC)
        assert schedule.get_battle_times(self.clan1)['rounds'] == [{
            'time': start_at,
            'title': 'Owner',
            'clan_a': self.clan1,
            'clan_b': self.owner,
            'start_at': start_at,
        }]

    def test_started_first_round(self):
        schedule = Schedule.objects.first()
        schedule.round_number = 1
        schedule.save()
        start_at = datetime.combine(schedule.date, time(12, 00)).replace(tzinfo=pytz.UTC)
        schedule.battles.create(
            clan_a=self.clan1,
            clan_b=self.clan2,
            round=1,
            start_at=start_at,
        )
        schedule.battles.create(
            clan_a=self.clan3,
            clan_b=self.clan4,
            round=1,
            start_at=start_at,
        )
        schedule.battles.create(
            clan_a=self.clan5,
            clan_b=None,
            round=1,
            start_at=start_at,
        )
        assert schedule.get_battle_times(self.clan1)['rounds'] == [{
            'time': start_at,
            'title': '1/4',
            'clan_a': self.clan1,
            'clan_b': self.clan2,
            'start_at': start_at,
        }, {
            'time': start_at + timedelta(minutes=30),
            'title': '1/2',
            'clan_a': None,
            'clan_b': None,
            'start_at': None,
        }, {
            'time': start_at + timedelta(minutes=60),
            'title': 'Final',
            'clan_a': None,
            'clan_b': None,
            'start_at': None,
        }, {
            'time': start_at + timedelta(minutes=90),
            'title': 'Owner',
            'clan_a': self.owner,
            'clan_b': None,
            'start_at': None,
        }]

    def test_started_second_round(self):
        schedule = Schedule.objects.first()
        schedule.round_number = 2
        schedule.save()
        start_at = datetime.combine(schedule.date, schedule.prime_time).replace(tzinfo=pytz.UTC)
        schedule.battles.create(
            clan_a=self.clan1,
            clan_b=self.clan3,
            round=2,
            start_at=start_at + timedelta(minutes=30, seconds=15),
        )
        schedule.battles.create(
            clan_a=self.clan5,
            clan_b=None,
            round=2,
            start_at=start_at + timedelta(minutes=30),
        )
        assert schedule.get_battle_times(self.clan1)['rounds'] == [{
            'time': start_at,
            'title': '1/4',
            'clan_a': None,
            'clan_b': None,
            'start_at': None,
        }, {
            'time': start_at + timedelta(minutes=30),
            'title': '1/2',
            'clan_a': self.clan1,
            'clan_b': self.clan3,
            'start_at': start_at + timedelta(minutes=30, seconds=15),
        }, {
            'time': start_at + timedelta(minutes=60),
            'title': 'Final',
            'clan_a': None,
            'clan_b': None,
            'start_at': None,
        }, {
            'time': start_at + timedelta(minutes=90),
            'title': 'Owner',
            'clan_a': self.owner,
            'clan_b': None,
            'start_at': None,
        }]

    def test_started_owner(self):
        schedule = Schedule.objects.first()
        schedule.round_number = 2
        schedule.save()
        start_at = datetime.combine(schedule.date, schedule.prime_time).replace(tzinfo=pytz.UTC)
        schedule.battles.create(
            clan_a=self.clan1,
            clan_b=self.clan3,
            round=2,
            start_at=start_at + timedelta(minutes=30, seconds=15),
        )
        schedule.battles.create(
            clan_a=self.clan5,
            clan_b=None,
            round=2,
            start_at=start_at + timedelta(minutes=30),
        )
        assert schedule.get_battle_times(self.owner)['rounds'] == [{
            'time': datetime.combine(schedule.date, time(13, 30)).replace(tzinfo=pytz.UTC),
            'title': 'Owner',
            'clan_a': schedule.owner,
            'clan_b': None,
            'start_at': None,
        }]



from scheduler.views import get_active_clan_schedules_by_date
class TestSearchCorrectProvinces(TestCase):
    def setUp(self):
        self.clan1, self.clan2, self.clan3, self.owner = create_clans(3, owner=True)
        schedule = Schedule.objects.create(
            front_id='front_id',
            front_name='front',
            province_id='province_id',
            province_name='province',
            arena_id='arena_id',
            arena_name='arena',
            server='server',
            date='2017-01-01',
            prime_time='12:00',
            battles_start_at='2017-01-01T12:00:00Z',
            round_number=2,
            owner=self.owner,
        )
        ProvinceBattles.objects.create(
            schedule=schedule,
            clan_a=self.clan1,
            clan_b=self.clan2,
            round=1,
            start_at='2017-01-01T12:00:00Z'
        )
        ProvinceBattles.objects.create(
            schedule=schedule,
            clan_a=self.clan3,
            clan_b=None,
            round=1,
            start_at='2017-01-01T12:00:00Z'
        )
        ProvinceBattles.objects.create(
            schedule=schedule,
            clan_a=self.clan1,
            clan_b=self.clan3,
            round=2,
            start_at='2017-01-01T12:00:00Z'
        )

    def test_lost_on_first_round(self):
        assert get_active_clan_schedules_by_date(self.clan2, '2017-01-01') == []

    def test_win_first_round(self):
        assert len(get_active_clan_schedules_by_date(self.clan3, '2017-01-01')) == 1

    def test_owner_has_battle(self):
        assert len(get_active_clan_schedules_by_date(self.owner, '2017-01-01')) == 1
