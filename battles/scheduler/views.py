from django.views import View
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.db import IntegrityError
from django.core.serializers.json import DjangoJSONEncoder

from datetime import datetime, timedelta

# Create your views here.


from .models import Clan, Schedule, Province
from .wgconnect import get_clan_data, normalize_provinces_data, WGClanBattles


def get_today():
    dt = datetime.now()
    # MSK Prime_time  starts at 9 AM UTC
    if dt.hour < 9:
        dt = dt - timedelta(days=1)
    return dt.date()


def get_battle_date(battle_dt):
    # MSK Prime_time  starts at 9 AM UTC
    return (battle_dt - timedelta(hours=9)).date()


class MyDjangoJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_json'):
            return o.to_json()
        return super().default(o)


def get_active_clan_schedules_by_date(clan, date):
    schedules = Schedule.objects.select_related('province'). \
        prefetch_related('competitors').prefetch_related('attackers').filter(
            date__gte=date). \
        exclude(status='FINISHED'). \
        filter(
            Q(owner=clan) |
            Q(attackers=clan) |
            Q(competitors=clan) |
            Q(battles__clan_a=clan) |
            Q(battles__clan_b=clan)
        )
    result = []
    for schedule in schedules:
        if schedule.round_number is None:
            result.append(schedule)
        elif any((clan == i.clan_a or clan == i.clan_b)
                 for i in schedule.battles.filter(round=schedule.round_number)):
            result.append(schedule)
    return result


class FetchClanDataView(View):
    def get(self, request, *args, **kwargs):
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
        today_schedule = get_active_clan_schedules_by_date(clan, today)
        province_ida = {
            (s.province.front_id, s.province.province_id)
            for s in today_schedule
        }

        # province_ida.setdefault(s.province.front_id, []).append(s.province.province_id)
        # update DB records for schedules and related provinces
        self.update(clan.id, province_ida)

        predicates = [
            lambda schedule, clan: clan == schedule.owner,
            lambda schedule, clan: clan in schedule.competitors.all(),
            lambda schedule, clan: clan in schedule.attackers.all(),
            lambda schedule, clan: schedule.battles.filter(round=schedule.round_number).filter(Q(clan_a=clan) | Q(clan_b=clan)),
        ]

        today_schedule = get_active_clan_schedules_by_date(clan, today)
        provinces_data = {}
        for schedule in set(today_schedule):
            province_id = schedule.province.province_id
            battles = schedule.get_battle_times(clan)
            if not battles:
                continue

            # if clan not in attackers/competitors/owner, skip the province
            if not any(predicate(schedule, clan) for predicate in predicates):
                continue

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

    # def province_status(self, date, data):
    #     # statuses: ['not started', 'started', 'finished', None]
    #     # | 0 ..... 9 ..... 17 ..... 18 ..... 19 ..... 20 ..... 21 ..... 22 ..... 23 ..... 24 | 0 ..... 9 ...........
    #     # Finished  | Not Started ........... | Started ....... | Finished ................... Finished | Not Started
    #     # Finished  | Not Started ........... | Started ....... | Finished ................... Finished | Not Started
    #     dt = data['battles_start_at']
    #     if dt.hour() < 9:
    #         pass

    # @staticmethod
    # def update_clans_info(clan_ids):
    #     clan_ids = [i.id for i in clan_ids if not i.tag]
    #     if clan_ids:
    #         for clan_data in wgn.clans.info(clan_id=clan_ids, fields=['clan_id', 'tag']).values():
    #             Clan.objects.update_or_create(id=clan_data['clan_id'], defaults={
    #                 'tag': clan_data['tag']
    #             })

    @staticmethod
    def update_province(province_data):
        attackers = province_data['attackers']
        competitors = province_data['competitors']
        active_battles = province_data['active_battles']
        battles_start_at = province_data['battles_start_at']
        battle_date = get_battle_date(battles_start_at)
        status = province_data['status']

        print("Updating province " + province_data['province_id'])

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
            all_enemies += [b['clan_a']['clan_id'] for b in active_battles]
            all_enemies += [b['clan_b']['clan_id'] for b in active_battles]
            all_enemies = list(set(all_enemies) - {owner_clan_id})

        if not all_enemies:
            return

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
            defaults={
                'server': province_data['server'],
                'arena_id': province_data['arena_id'],
                'owner': owner,
                'round_number': round_number,
                'battles_start_at': province_data['battles_start_at'],
            },
        )[0]

        print(f"Created schedule {schedule}")

        try:
            schedule.competitors.set(competitors)
        except IntegrityError:
            existing = {i.id for i in Clan.objects.filter(id__in=competitors)}
            for clan_id in set(competitors) - existing:
                Clan.objects.create(id=clan_id)
            schedule.competitors.set(competitors)

        try:
            schedule.attackers.set(attackers)
        except IntegrityError:
            existing = {i.id for i in Clan.objects.filter(id__in=attackers)}
            for clan_id in set(attackers) - existing:
                Clan.objects.create(id=clan_id)
            schedule.attackers.set(attackers)

        for battle in active_battles:
            print(f"Create battle {battle}")
            schedule.battles.update_or_create(
                clan_a_id=battle['clan_a']['clan_id'],
                clan_b_id=battle['clan_b']['clan_id'],
                round=battle['round'],
                defaults={'start_at': battle['start_at']},
            )

    def update(self, clan_id, provinces_ids):
        provinces_data = WGClanBattles(clan_id, provinces_ids).get_clan_battles()
        # --- Update provinces data in DB ---
        for province_data in provinces_data:
            self.update_province(province_data)
        return [p['province_id'] for p in provinces_data]



import wargaming
from django.conf import settings
from django.http import StreamingHttpResponse
from itertools import count


class UpdateAllProvinces(View):
    @staticmethod
    def list_all():
        yield 'Updating all database'
        wot = wargaming.WoT(settings.WARGAMING_API, 'ru', 'ru')
        wgn = wargaming.WGN(settings.WARGAMING_API, 'ru', 'ru')
        no_tags = {str(i.id): i for i in Clan.objects.filter(tag='')}
        total = len(no_tags)
        for i in range(0, total, 100):
            clans_req = list(no_tags.keys())[i:i+100]
            for clan_id, clan_data in wgn.clans.info(clan_id=clans_req, fields='tag').items():
                no_tags[clan_id].tag = clan_data['tag']
                no_tags[clan_id].save()
            yield 'Done %s/%s clans' % (i + 100, len(no_tags))
        yield 'Done'

        fronts = wot.globalmap.fronts()
        yield "Get %s fronts" % len(fronts)
        for front_data in fronts:
            front_id = front_data['front_id']
            for page_no in count():
                provinces = wot.globalmap.provinces(front_id=front_id, page_no=page_no + 1)
                if len(provinces) == 0:
                    break
                yield f"Get %s provinces on front {front_id}" % (100 * page_no + len(provinces))
                for province in normalize_provinces_data(provinces):
                    FetchClanDataView.update_province(province)
        yield "Done"

    def get(self, request, *args, **kwargs):
        response = StreamingHttpResponse(self.list_all())
        response['Access-Control-Allow-Origin'] = '*'
        return response
