
from django.conf import settings
from django.core.management.base import BaseCommand


from .utils import common

class Command(BaseCommand):
    help = 'Initializes the all JWKs from all user pools in Cognito.'

    def handle(self, *args, **options):
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




