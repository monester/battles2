from django.core.management.base import BaseCommand, CommandError
from scheduler.models import Schedule, Clan
from datetime import datetime, timedelta
import pytz


class Command(BaseCommand):
    def handle(self, *args, **options):
        now = datetime.now(tz=pytz.UTC)
        provinces = Schedule.objects.filter(date=(now - timedelta(hours=9)).date())
        for p in provinces:
            print(
                f'./manage.py fake '
                f'--province {p.province_id} '
                f'--prime {p.prime_time} '
                f'--owner {p.owner.tag} '
                f'--status {p.status} '
            )
