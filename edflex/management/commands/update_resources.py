from django.core.management.base import BaseCommand

from edflex.tasks import update_resources


class Command(BaseCommand):

    def handle(self, *args, **options):
        update_resources()
