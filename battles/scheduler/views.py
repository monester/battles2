from django.shortcuts import render
from django.views import View
from django.http import JsonResponse, Http404
from django.db.models import Q

from datetime import datetime, timedelta, time
from itertools import chain, groupby
from requests.exceptions import RequestException
import json

# Create your views here.


from .models import Clan, Schedule, Province, ProvinceBalltes
from .wgconnect import get_provinces_data, get_clan_related_provinces, get_clan_data


def get_today():
    dt = datetime.now()
    # MSK Prime_time  starts at 9 AM UTC
    if dt.hour < 9:
        dt = dt - timedelta(days=1)
    return dt.date()


def get_battle_date(battle_dt):
    # MSK Prime_time  starts at 9 AM UTC
    return (battle_dt - timedelta(hours=9)).date()


from django.core.serializers.json import DjangoJSONEncoder
class MyDjangoJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_json'):
            return o.to_json()
        return super().default(o)


class FetchClanDataView(View):
    def get(self, request, *args, **kwargs):
        clan_id = int(kwargs.get('clan_id', 0))
        clan_tag = kwargs['clan_tag'].upper()
        try:
            clan = Clan.objects.get(tag=clan_tag)
        except Clan.DoesNotExist:
            clan_data = get_clan_data(clan_tag)
            if clan_data:
                clan = Clan.objects.update_or_create(
                    id=clan_data['clan_id'], 
                    defaults={'tag': clan_data['tag']})[0]
            else:
                raise Http404("Clan not found")

        today = get_today()

        # list involved provinces
        provinces_id = self.update(clan.id)
        print (provinces_id)
        today_battles = Schedule.objects.filter(
            province__province_id__in=provinces_id,
            date__gte=today
        ).filter(Q(owner=clan) | Q(attackers=clan) | Q(competitors=clan))

        provinces_data = {}
        for s in set(today_battles):
            province_id = s.province.province_id
            battles = s.get_battle_times(clan)
            if province_id not in provinces_data:
                provinces_data[province_id] = battles
            else:
                provinces_data[province_id]['rounds'] += battles['rounds']

        for province_data in provinces_data.values():
            province_data['rounds'].sort(key=lambda x: x['time'])

        response = JsonResponse({
            'clan': {'clan_id': clan.id, 'tag': clan.tag},
            'provinces': list(provinces_data.values()),
        }, encoder=MyDjangoJSONEncoder)
        response['Access-Control-Allow-Origin'] = '*'
        return response

    def province_status(self, date, data):
        # statuses: ['not started', 'started', 'finished', None]
        # | 0 ..... 9 ..... 17 ..... 18 ..... 19 ..... 20 ..... 21 ..... 22 ..... 23 ..... 24 | 0 ..... 9 ...........
        # Finished  | Not Started ........... | Started ....... | Finished ................... Finished | Not Started
        # Finished  | Not Started ........... | Started ....... | Finished ................... Finished | Not Started
        dt = data['battles_start_at']
        if dt.hour() < 9:
            pass

    # @staticmethod
    # def update_clans_info(clan_ids):
    #     clan_ids = [i.id for i in clan_ids if not i.tag]
    #     if clan_ids:
    #         for clan_data in wgn.clans.info(clan_id=clan_ids, fields=['clan_id', 'tag']).values():
    #             Clan.objects.update_or_create(id=clan_data['clan_id'], defaults={
    #                 'tag': clan_data['tag']
    #             })


    def update(self, clan_id):
        clan_provinces = get_clan_related_provinces(clan_id)
        provinces_data = get_provinces_data(clan_provinces)

        # --- Update provinces data in DB ---
        for province_data in provinces_data:
            attackers = province_data['attackers']
            competitors = province_data['competitors']
            active_battles = province_data['active_battles']
            battles_start_at = province_data['battles_start_at']
            battle_date = get_battle_date(battles_start_at)
            front_id=province_data['front_id'],
            province_id=province_data['province_id'],
            status = province_data['status']

            owner_clan_id = province_data['owner_clan_id']
            if owner_clan_id:
                owner = Clan.objects.get_or_create(id=province_data['owner_clan_id'])[0]
            else:
                owner = None

            # use this number only if battles have been started
            # usually if contains irrelevant data before starting battles
            round_number = province_data['round_number'] if status == "STARTED" else None

            all_enemies = attackers + competitors
            if status == 'STARTED':
                all_enemies += [b['clan_a'] for b in active_battles]
                all_enemies += [b['clan_b'] for b in active_battles]
                all_enemies = list(set(all_enemies) - set([owner]))

            if not attackers and not competitors:
                continue

            print(f"Updating {province_data['province_id']} for {battle_date}")

            # get province
            province = Province.objects.get_or_create(
                front_id=province_data['front_id'],
                province_id=province_data['province_id'],
                defaults={
                    'province_name': province_data['province_name'],
                    'arena_id': province_data['arena_id'],
                    'arena_name': province_data['arena_name'],
                    'prime_time': province_data['prime_time'],
                },
            )[0]


            # update scheduled battle info
            schedule = province.schedules.update_or_create(
                date=battle_date,
                arena_id=province_data['arena_id'],
                owner=owner,
                defaults={
                    'round_number': round_number,
                    'battles_start_at': province_data['battles_start_at'],
                },
            )[0]
            schedule.competitors.set(competitors)
            schedule.attackers.set(attackers)

            for battle in active_battles:
                schedule.battles.update_or_create(
                    clan_a=battle['clan_a'],
                    clan_b=battle['clan_b'],
                    round=battle['round'],
                    defaults={'start_at': battle['start_at']},
                )
        return [p['province_id'] for p in provinces_data]


class ShowClanSchedule(View):
    @property
    def today(self):
        return get_today()

    def get(self, request, *args, **kwargs):
        clan_id = kwargs['clan_id']
        clan_tag = kwargs['clan_tag']

        clan = Clan.objects.get_or_create(id=int(clan_id))

        for schedule in Schedule.get_clan_involved(date=self.today, clan=clan):
            schedule.get_battle_times(clan)
        return JsonResponse({'provinces': clan_provinces})
