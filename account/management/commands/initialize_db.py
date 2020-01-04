
from django.conf import settings
from django.core.management.base import BaseCommand
import os
import uuid

from account.models import Account, Organization
from caracal.common import stripe_utils
from caracal.common.aws_utils import cognito, dynamodb

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
        if stage not in ['development', 'staging', 'production', 'testing']:
            print("Unknown settings: " + options['settings'])
            return

        print("Stage: %s\n"
              "Cognito User Pool: %s\n"
              "Postgres Host: %s\n"
              "Postgres Database: %s\n" %
              (stage, settings.COGNITO_USER_POOL_NAME, settings.DATABASES['default']['HOST'], settings.DATABASE_NAME))

        response = input("Do you want to clear the database and update dummy data? [clear/update/exit]\n").lower()

        if response == 'clear':

            common.clear_all_content()

            # create superuser
            Account.objects.create_superuser(os.environ['CARACAL_OVERLORD_EMAIL'],
                                             os.environ['CARACAL_OVERLORD_PASSWORD'])

            # create dummy user
            dummy_org = Organization.objects.create(name='Dummy Inc.', short_name=settings.DUMMY_SHORT_NAME)

            dummy_cognito_uid = cognito.create_user(settings.DUMMY_EMAIL, 'Kigali123')

            dummy_user = Account.objects.create(uid_cognito=dummy_cognito_uid, organization=dummy_org,
                                                email=settings.DUMMY_EMAIL, name='Dummy Dumbo',
                                                phone_number='+250780177236', is_admin=True)

            cognito.confirm_account(settings.DUMMY_EMAIL)

            """
            # create Stripe Customer
            customer = stripe_utils.create_customer(dummy_user.email, dummy_user.name, dummy_user.phone_number)
            plan = stripe_utils.get_plan('Individual')
            subscription = stripe_utils.create_subscription(customer['customer_id'], plan['id'])
            dummy_org.stripe_customer_id = customer['customer_id']
            dummy_org.stripe_plan_id = plan['id']
            dummy_org.stripe_subscription_id = subscription['id']
            dummy_org.stripe_subscription_status = subscription['status']
            dummy_org.save()            
            """

            # create credentials for S3
            password = str(uuid.uuid4()).split('-')[0]
            dynamodb.create_dynamodb_credentials(settings.DUMMY_SHORT_NAME, 'admin', password, ['all'])

        elif response == 'update':
            try:
                dummy_user = Account.objects.get(email=settings.DUMMY_EMAIL)
            except Account.DoesNotExist:
                print("dummy account does not exist. clear first")
                return
            else:
                common.clear_dummy_content(dummy_user)

        else:
            return

        common.add_dummy_alerts(dummy_user)
        common.add_dummy_changes(dummy_user)
        common.add_dummy_collars(dummy_user)
        common.add_dummy_radios(dummy_user)







