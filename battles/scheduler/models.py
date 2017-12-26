import pytz
import math
from itertools import chain
from datetime import date, time, datetime, timedelta

from django.db import models
from django.db.models import Q


class Schedule(models.Model):
    """Store an attack on province on selected date

    """
    province = models.ForeignKey('Province', on_delete=models.CASCADE, related_name='schedules')
    server = models.CharField(max_length=10)
    arena_id = models.CharField(null=True, max_length=255)
    date = models.DateField()
    battles_start_at = models.DateTimeField()
    attackers = models.ManyToManyField('Clan', related_name='+')
    competitors = models.ManyToManyField('Clan', related_name='+')
    owner = models.ForeignKey('Clan', on_delete=models.SET_NULL, null=True, related_name='+')
    is_landing = models.BooleanField(default=False)
    round_number = models.IntegerField(null=True)
    status = models.CharField(null=True, max_length=8, choices=(
        ('NOT_STARTED', 'NOT_STARTED'), ('STARTED', 'STARTED'), ('FINISHED', 'FINISHED')))

    def __repr__(self):
        return f"<Schedule {self.province.province_id}@{self.date}>"

    @property
    def all_clans(self):
        clans = list(self.attackers.all()) + list(self.competitors.all())
        if self.status == 'STARTED':
            for battle in self.battles.filter(round=self.round_number):
                clans += [battle.clan_a, battle.clan_b]
        return list(set(clans))

    def get_battle_times(self, clan):
        clans_count = len(set(self.all_clans) - {self.owner})

        if clans_count > 0:
            rounds = math.ceil(math.log(clans_count, 2)) + (self.round_number or 1)
        else:
            # no one attacking this province on this day
            rounds = 0

        today = datetime.combine(self.date, self.province.prime_time).replace(tzinfo=pytz.UTC)
        existing_battles = {
            battle.round - 1: battle
            for battle in self.battles.filter(Q(clan_a=clan) | Q(clan_b=clan))
        }

        if self.owner == clan:
            mode = 'Defence'
            first_round = rounds - 1
        else:
            mode = 'Tournament' if clan in self.competitors.all() else 'By Land'
            first_round = 0

        # fill time table with rounds for specified clan
        battle_times = []
        for round_number in range(first_round, rounds):
            if round_number == rounds - 2:
                title = 'Final'
            elif round_number == rounds - 1:
                # battle with owner
                if not self.owner:
                    break
                title = 'Owner'
            else:
                title = '1/%s' % pow(2, rounds - round_number - 2)

            if round_number in existing_battles:
                clan_a = existing_battles[round_number].clan_a
                clan_b = existing_battles[round_number].clan_b
                start_at = existing_battles[round_number].start_at
            elif round_number == rounds - 1:
                # on last round there is always owner on one side
                clan_a = self.owner
                clan_b = None
                start_at = None
            else:
                clan_a = None
                clan_b = None
                start_at = None

            battle_times.append({
                'clan_a': clan_a,
                'clan_b': clan_b,
                'time': today + timedelta(minutes=30) * round_number,
                'start_at': start_at,
                'title': title,
            })

        return {
            'owner': self.owner.id if self.owner else None,
            'attackers': [c.id for c in chain(self.attackers.all(), self.competitors.all())],
            'province_id': self.province.province_id,
            'arena_name': self.province.arena_name,
            'province_name': self.province.province_name,
            'prime_time': self.province.prime_time,
            'rounds': battle_times,
            'mode': mode,
            'server': self.server,
        }

    @classmethod
    def get_clan_involved(cls, date, clan):
        cls.objects.filter(Q(attackers=clan) | Q(competitors=clan) | Q(owner=clan), date=date)


class ProvinceBattles(models.Model):
    schedule = models.ForeignKey('Schedule', on_delete=models.CASCADE, related_name='battles')
    clan_a = models.ForeignKey('Clan', on_delete=models.CASCADE, related_name='+', null=True)
    clan_b = models.ForeignKey('Clan', on_delete=models.CASCADE, related_name='+', null=True)
    round = models.IntegerField()
    start_at = models.DateTimeField()

    def __repr__(self):
        return f'<ProvinceBattles {self.clan_a.id} vs {self.clan_b.id} {self.schedule.province.province_id}@{self.start_at.date()} [round: {self.round}]>'


class Clan(models.Model):
    tag = models.CharField(max_length=5)

    def to_json(self):
        return {'id': self.id, 'tag': self.tag}

    def __repr__(self):
        return f'<Clan {self.id}: {self.tag}>'


class Province(models.Model):
    front_id = models.CharField(max_length=255)
    arena_id = models.CharField(max_length=255)
    arena_name = models.CharField(max_length=255)
    province_id = models.CharField(max_length=255)
    province_name = models.CharField(max_length=255)
    prime_time = models.TimeField()

    def __repr__(self):
        return f"<Province {self.province_id}>"

    def get_schedule_for_date(self, scheduled_date):
        try:
            return self.schedules.exclude(status='FINISHED'). \
                prefetch_related('attackers', 'competitors'). \
                select_related('owner').get(date=scheduled_date)
        except Schedule.DoesNotExist:
            return None
