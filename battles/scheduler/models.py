import pytz
import math
from itertools import chain
from datetime import date, time, datetime, timedelta

from django.db import models
from django.db.models import Q


def get_rounds_titles(clans_count, current_round, owner=None):
    """Return title for rounds
    >>> get_rounds_titles(5, 1, True)
    ['1/4', '1/2', 'Final', 'Owner']
    >>> get_rounds_titles(5, 1, False)
    ['1/4', '1/2', 'Final']
    >>> get_rounds_titles(2, 1, True)
    ['Final', 'Owner']
    >>> get_rounds_titles(2, 1, False)
    ['Final']
    >>> get_rounds_titles(1, 1, True)
    ['Owner']
    >>> get_rounds_titles(3, 2, True)
    ['1/4', '1/2', 'Final', 'Owner']
    """
    titles = []
    if clans_count:
        total_rounds = current_round + math.ceil(math.log(clans_count, 2)) - 2
        for i in range(total_rounds):
            titles.append('1/%s' % pow(2, total_rounds - i))
        if clans_count > 1:
            titles.append('Final')
        if owner:
            titles.append('Owner')
    return titles


class Schedule(models.Model):
    """Store an attack on province on selected date

    """
    front_id = models.CharField(max_length=255)
    front_name = models.CharField(max_length=255)
    province_id = models.CharField(max_length=255)
    province_name = models.CharField(max_length=255)
    arena_id = models.CharField(max_length=255)
    arena_name = models.CharField(max_length=255)
    server = models.CharField(max_length=10)
    date = models.DateField()
    prime_time = models.TimeField()
    battles_start_at = models.DateTimeField()
    pretenders = models.ManyToManyField('Clan', related_name='+')
    owner = models.ForeignKey('Clan', on_delete=models.SET_NULL, null=True, related_name='+')
    landing_type = models.CharField(null=True, max_length=10, choices=(
        (None, 'By land'), ('tournament', 'tournament')
    ))
    round_number = models.IntegerField(null=True)
    # is status needed?
    status = models.CharField(null=True, max_length=8, choices=(
        ('NOT_STARTED', 'NOT_STARTED'),
        ('STARTED', 'STARTED'),
        ('FINISHED', 'FINISHED')
    ))

    def __repr__(self):
        return f"<Schedule {self.province_id}@{self.date}>"

    @property
    def all_clans(self):
        if self.round_number:
            clans = set()
            for battle in self.battles.filter(round=self.round_number):
                clans.update([battle.clan_a, battle.clan_b])
            return clans - {None}
        else:
            return self.pretenders.all()

    def get_battle_times(self, clan):
        clans_count = len(set(self.all_clans) - {self.owner})

        today = datetime.combine(self.date, self.prime_time).replace(tzinfo=pytz.UTC)
        existing_battles = {
            battle.round - 1: battle
            for battle in self.battles.filter(Q(clan_a=clan) | Q(clan_b=clan))
        }

        round_titles = get_rounds_titles(clans_count, self.round_number or 1, self.owner)
        total_rounds = len(round_titles)
        if self.owner == clan:
            mode = 'Defence'
            first_round = total_rounds - 1 if total_rounds > 0 else 0
        else:
            mode = self.get_landing_type_display()
            first_round = 0

        # fill time table with rounds for specified clan
        battle_times = []
        for round_number in range(first_round, len(round_titles)):
            round_title = round_titles[round_number]
            if round_number in existing_battles:
                clan_a = existing_battles[round_number].clan_a
                clan_b = existing_battles[round_number].clan_b
                start_at = existing_battles[round_number].start_at
            elif round_number == total_rounds - 1:
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
                'title': round_title,
            })

        return {
            'owner': self.owner.id if self.owner else None,
            'province_id': self.province_id,
            'arena_name': self.arena_name,
            'province_name': self.province_name,
            'prime_time': self.prime_time,
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
        return (
            f'<ProvinceBattles {self.clan_a_id} vs {self.clan_b_id} '
            f'{self.schedule.province_id}@{self.start_at.date()} [round: {self.round}]>'
        )


class Clan(models.Model):
    tag = models.CharField(max_length=5)

    def to_json(self):
        return {'id': self.id, 'tag': self.tag}

    def __repr__(self):
        return f'<Clan {self.id}: {self.tag}>'
