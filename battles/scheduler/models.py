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

    def get_battle_times(self, clan):
        clans_count = self.attackers.count() + self.competitors.count()
        rounds = math.ceil(math.log(clans_count, 2)) + (self.round_number or 1) - 1

        today = datetime.combine(self.date, self.province.prime_time).replace(tzinfo=pytz.UTC)
        existing_battles = {
            battle.round: battle
            for battle in self.battles.all()
            if clan == battle.clan_a or clan == battle.clan_b
        }

        # print(existing_battles)
        battle_times = []
        if self.owner == clan:
            mode = 'Defence'
        else:
            mode = 'Tournament' if clan in self.competitors.all() else 'By Land'
            for round_number in range(rounds):
                title = 'Final' if round_number == rounds - 1 else '1/%s' % pow(2, rounds - round_number - 1)

                if round_number in existing_battles:
                    clan_a = existing_battles[round_number].clan_a
                    clan_b = existing_battles[round_number].clan_b
                else:
                    clan_a = None
                    clan_b = None

                battle_times.append({
                    'clan_a': clan_a,
                    'clan_b': clan_b,
                    'time': today + timedelta(minutes=30) * round_number,
                    'title': title,
                })

        # if province is owned by some clan add one more round
        if self.owner:
            battle_times.append({
                'clan_a': self.owner,
                'clan_b': None,
                'time': today + timedelta(minutes=30) * rounds,
                'title': 'Owner',
            })

        return {
            'owner': self.owner.id if self.owner else None,
            'attackers': [c.id for c in chain(self.attackers.all(), self.competitors.all())],
            'province_id': self.province.province_id,
            'province_name': self.province.province_name,
            'prime_time': self.province.prime_time,
            'rounds': battle_times,
            'mode': mode,
        }

    @classmethod
    def get_clan_involved(cls, date, clan):
        cls.objects.filter(Q(attackers=clan) | Q(competitors=clan) | Q(owner=clan), date=date)


class ProvinceBalltes(models.Model):
    schedule =  models.ForeignKey('Schedule', on_delete=models.CASCADE, related_name='battles')
    clan_a = models.ForeignKey('Clan', on_delete=models.CASCADE, related_name='+')
    clan_b = models.ForeignKey('Clan', on_delete=models.CASCADE, related_name='+')
    round = models.IntegerField()
    start_at = models.DateTimeField()

    def __repr__(self):
        return f'<ProvinceBalltes {self.clan_a.id} vs {self.clan_b.id} {self.schedule.province.province_id}@{self.start_at.date()} [round: {self.round}]>'


class Clan(models.Model):
    tag = models.CharField(max_length=5)

    def to_json(self):
        return {'id': self.id, 'tag': self.tag}

    def __repr__(self):
        return f'<Clan {self.tag}>'


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
