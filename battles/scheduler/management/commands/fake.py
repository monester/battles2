import random
from datetime import datetime, timedelta
from itertools import zip_longest
import pytz

from django.core.management.base import BaseCommand, CommandError
from scheduler.models import Schedule, Clan

provinces_data = [{
    'arena_id': '47_canada_a',
    'arena_name': 'Тихий берег',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '20:15',
    'province_id': 'agadir',
    'province_name': 'Агадир',
    'server': 'RU6'
}, {
    'arena_id': '08_ruinberg',
    'arena_name': 'Руинберг',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '19:15',
    'province_id': 'amizmiz',
    'province_name': 'Амизмиз',
    'server': 'RU6',
}, {
    'arena_id': '02_malinovka',
    'arena_name': 'Малиновка',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '17:15',
    'province_id': 'azrou',
    'province_name': 'Азру',
    'server': 'RU6',
}, {
    'arena_id': '06_ensk',
    'arena_name': 'Энск',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '18:15',
    'province_id': 'benimellal',
    'province_name': 'Бени-Меллаль',
    'server': 'RU6',
}, {
    'arena_id': '35_steppes',
    'arena_name': 'Степи',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '18:15',
    'province_id': 'casablanca',
    'province_name': 'Касабланка',
    'server': 'RU6',
}, {
    'arena_id': '04_himmelsdorf',
    'arena_name': 'Химмельсдорф',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '17:00',
    'province_id': 'errachidia',
    'province_name': 'Эр-Рашидия',
    'server': 'RU6',
}, {
    'arena_id': '07_lakeville',
    'arena_name': 'Ласвилль',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '20:00',
    'province_id': 'essaouira',
    'province_name': 'Эс-Сувейра',
    'server': 'RU6',
}, {
    'arena_id': '18_cliff',
    'arena_name': 'Утёс',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '16:15',
    'province_id': 'fes',
    'province_name': 'Фес',
    'server': 'RU6',
}, {
    'arena_id': '10_hills',
    'arena_name': 'Рудники',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '19:00',
    'province_id': 'marrakesh',
    'province_name': 'Марракеш',
    'server': 'RU6',
}, {
    'arena_id': '11_murovanka',
    'arena_name': 'Мурованка',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '18:00',
    'province_id': 'ouarzazate',
    'province_name': 'Уарзазат',
    'server': 'RU6',
}, {
    'arena_id': '36_fishing_bay',
    'arena_name': 'Рыбацкая бухта',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '17:00',
    'province_id': 'rabat',
    'province_name': 'Рабат',
    'server': 'RU6',
}, {
    'arena_id': '28_desert',
    'arena_name': 'Песчаная река',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '19:15',
    'province_id': 'safi',
    'province_name': 'Сафи',
    'server': 'RU6',
}, {
    'arena_id': '29_el_hallouf',
    'arena_name': 'Эль-Халлуф',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '16:00',
    'province_id': 'tangier',
    'province_name': 'Танжер',
    'server': 'RU6',
}, {
    'arena_id': '19_monastery',
    'arena_name': 'Монастырь',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '16:00',
    'province_id': 'taza',
    'province_name': 'Таза',
    'server': 'RU6',
}, {
    'arena_id': '23_westfeld',
    'arena_name': 'Вестфилд',
    'front_id': 'event_gambit_ru_l_league3',
    'front_name': 'Элитный',
    'prime_time': '20:00',
    'province_id': 'tigezmirt',
    'province_name': 'Тихезмирт',
    'server': 'RU6'
}]


class Command(BaseCommand):
    help = 'Create fake battle for province'

    def add_arguments(self, parser):
        parser.add_argument('--prime')
        parser.add_argument('--clans', type=int, default=3)
        parser.add_argument('--owner')
        parser.add_argument('--province')
        parser.add_argument('--status')
        parser.add_argument('--round', type=int)

    def handle(self, *args, **options):
        all_clans = list(Clan.objects.all())

        if options['province']:
            province_data = [i for i in provinces_data
                             if i['province_id'] == options['province']][0]
        else:
            province_data = provinces_data[random.randint(0, len(provinces_data) - 1)]
        province_id = province_data.pop('province_id')
        now = datetime.now(tz=pytz.UTC).replace(microsecond=0)
        today = (now - timedelta(hours=9)).date()
        if options['prime']:
            hour, minute, *_ = map(int, options['prime'].split(":"))
            battles_start_at = now.replace(hour=hour, minute=minute, second=0) + timedelta(hours=1)
            if battles_start_at < now:
                battles_start_at += timedelta(days=1)
        else:
            battles_start_at = now.replace(minute=0, second=0) + timedelta(hours=1)
        province_data['battles_start_at'] = battles_start_at
        province_data['prime_time'] = prime_time = options['prime'] or battles_start_at.time()
        province_data['round_number'] = round_number = options['round']
        if options['round']:
            status = 'STARTED'
        else:
            status = options['status'] if options['status'] != 'None' else None
        province_data['status'] = status
        if options['owner'] is None:
            owner = all_clans[random.randint(0, len(all_clans) - 1)]
            all_clans.remove(owner)
        elif options['owner'] == 'None':
            owner = None
        else:
            owner = Clan.objects.get(tag=options['owner'])
            all_clans.remove(owner)

        province_data['owner'] = owner

        # 1: 2^(1-1)=1  - [0,1,2,3,4,5,6,7]
        # 2: 2^(2-1)=2  - [0,2,4,6]
        # 3: 2^(3-1)=4  - [0,4]
        # 4: 2^(4-1)=8  - [0]
        if status != 'FINISHED':
            clans = all_clans[0:options['clans']:pow(2, (round_number or 1) - 1)]
        else:
            clans = []
        print("-" * 80)
        print("Attacking clans : " + " ".join([c.tag for c in clans]))
        print("Owner           : %s" % owner.tag)
        print("-" * 80)

        print(
            f'./manage.py fake '
            f'--clans {len(clans)} '
            f'--province {province_id} '
            f'--prime {prime_time} '
            f'--owner {owner.tag} '
            f'--status {status} '
            f'--round {round_number} '
        )

        s = Schedule.objects.update_or_create(
            province_id=province_id,
            date=today,
            defaults=province_data,
        )[0]

        if status != 'FINISHED':
            s.pretenders.set(clans)
        if status is not None:
            if len(clans) == 1:
                clans.append(owner)
            s.battles.filter(round=round_number).delete()
            for clan_a, clan_b in zip_longest(clans[::2], clans[1::2]):
                s.battles.create(
                    clan_a=clan_a,
                    clan_b=clan_b,
                    round=round_number,
                    start_at=s.battles_start_at + timedelta(minutes=30) * (round_number - 1),
                )
                clan_a_tag = clan_a.tag
                clan_b_tag = clan_b and clan_b.tag
                print(f"ROUND {round_number}: {clan_a_tag} vs {clan_b_tag} on {s.province_id}")
