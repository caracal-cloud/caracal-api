
from django.conf import settings
from django.core.management.base import BaseCommand
import os

from account.models import Account
from activity.models import ActivityAlert, ActivityChange

from .utils import common

class Command(BaseCommand):
    help = 'Initializes the all JWKs from all user pools in Cognito.'

    def handle(self, *args, **options):

        try:
            x = os.environ['DEPLOYED']
            print('You must run this locally')
            return
        except:
            pass

        if options['settings'] is None:
            print("You must specify settings (eg. --settings=caracal.settings.development)")
            return

        stage = options['settings'].split('.')[-1]
        if stage not in ['development', 'staging', 'production']:
            print("Unknown settings: " + options['settings'])
            return

        print("Stage: %s\n"
              "Cognito User Pool: %s\n"
              "Postgres Host: %s\n"
              "Postgres Database: %s\n" %
              (stage, settings.COGNITO_USER_POOL_NAME, settings.DATABASES['default']['HOST'], settings.DATABASE_NAME))

        if input("Are you sure you want to clear the database and reinitialize it? [y/n]\n").lower() != "y":
            return

        common.clear_all_content()

        # create superuser
        superuser = Account.objects.create_superuser(os.environ['CARACAL_OVERLORD_EMAIL'],
                                                     os.environ['CARACAL_OVERLORD_PASSWORD'])

        # add dummy alerts
        alerts = [
            {
                'message': 'elephant Martin has not moved in 16 hours',
                'level': 'high'
            },
            {
                'message': 'elephant Marie has not moved in 8 hours',
                'level': 'high'
            },
            {
                'message': 'elephant Bosco has travel 42.5 km in the last 24 hours',
                'level': 'medium'
            },
            {
                'message': 'elephant James has travel 51.2 km in the last 24 hours',
                'level': 'medium'
            },
            {
                'message': 'no radio positions have been received in the last 12 hours',
                'level': 'low'
            },
            {
                'message': 'no Orbcomm collar positions have been received in the last 24 hours',
                'level': 'low'
            }
        ]

        for alert in alerts:
            ActivityAlert.objects.create(organization=superuser.organization, **alert)

        # add dummy changes
        changes = [
            {
                'message': 'Martin Ishimwe added an elephant collar account'
            },
            {
                'message': 'Roger Green dismissed alert (elephant Dumbo has travel 36.2 km in the last 24 hours)'
            },
            {
                'message': 'Martin Ishimwe added connected an ArcGIS Online account'
            },
            {
                'message': 'Roger Green added connected a Google Drive account'
            }
        ]

        for change in changes:
            ActivityChange.objects.create(organization=superuser.organization, account=superuser, **change)






