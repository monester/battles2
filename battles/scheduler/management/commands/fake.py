import random
from datetime import datetime, timedelta
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
        parser.add_argument('--create-rounds')
        parser.add_argument('--owner')

    def handle(self, *args, **options):
        clans = Clan.objects.all()[0:options['clans']]

        province_data = provinces_data[random.randint(0, len(provinces_data) - 1)]
        province_id = province_data.pop('province_id')
        now = datetime.now(tz=pytz.UTC).replace(microsecond=0)
        today = (now - timedelta(hours=9)).date()
        battles_start_at = now.replace(minute=0, second=0) + timedelta(hours=1)
        province_data['battles_start_at'] = battles_start_at
        province_data['prime_time'] = options['prime'] or battles_start_at.time()
        province_data['round_number'] = None
        province_data['status'] = None
        province_data['owner'] = options['owner'] and Clan.objects.get(tag=options['owner'])
        print(today)
        print(province_data)

        s = Schedule.objects.update_or_create(province_id=province_id, date=today,
                                              defaults=province_data)[0]
        s.pretenders.set(clans)
        print([i.tag for i in clans])
