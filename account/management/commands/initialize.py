
from django.conf import settings
from django.core.management.base import BaseCommand

from account.models import Account


class Command(BaseCommand):

    def handle(self, *args, **options):

        try:
            Account.objects.get(email=settings.OVERLORD_EMAIL)
        except Account.DoesNotExist:
            Account.objects.create_superuser(settings.OVERLORD_EMAIL, settings.OVERLORD_PASSWORD)
            # TODO: auto confirm...