from django.core.management.base import BaseCommand

from edflex.tasks import fetch_edflex_data


class Command(BaseCommand):

    def handle(self, *args, **options):
        fetch_edflex_data()
