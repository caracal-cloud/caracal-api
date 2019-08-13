
from django.conf import settings
from django.core.management.base import BaseCommand
import os
import uuid

from account.models import Account, Organization
from activity.models import ActivityAlert, ActivityChange
from auth import cognito
from caracal.common import aws

from .utils import common

class Command(BaseCommand):
    help = 'Initializes the all JWKs from all user pools in Cognito.'

    def handle(self, *args, **options):

        try:
            os.environ['DEPLOYED']
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
        Account.objects.create_superuser(os.environ['CARACAL_OVERLORD_EMAIL'], os.environ['CARACAL_OVERLORD_PASSWORD'])

        # create dummy user
        dummy_org = Organization.objects.create(name='Dummy Inc.', short_name=settings.DUMMY_SHORT_NAME)
        dummy_user = Account.objects.create_user(settings.DUMMY_EMAIL, 'Kigali123',
                                                 cognito.get_cognito_idp_client(),
                                                 organization=dummy_org,
                                                 name='Dummy Dumbo',
                                                 phone_number='+250780177234',
                                                 is_admin=True)
        cognito.confirm_user(settings.DUMMY_EMAIL)

        # create credentials for S3
        password = str(uuid.uuid4()).split('-')[0]
        aws.create_dynamo_credentials(settings.DUMMY_SHORT_NAME, 'admin', password, ['all'])

        common.add_dummy_alerts(dummy_user)
        common.add_dummy_changes(dummy_user)
        common.add_dummy_collars(dummy_user)






