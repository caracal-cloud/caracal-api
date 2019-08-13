
import datetime
from django.conf import settings
from django.utils import timezone
import json
import random
import uuid

from activity.models import ActivityAlert, ActivityChange
from account.models import Account, Organization
from auth import cognito

from caracal.common import aws, constants
from caracal.common.models import RealTimeAccount, RealTimeIndividual, RealTimePosition, RealTimePositionHash
from drives.models import DriveFileAccount


def add_dummy_alerts(account):
    print('...adding dummy alerts')
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
        ActivityAlert.objects.create(organization=account.organization, **alert)


def add_dummy_changes(account):
    print('...adding dummy changes')
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
        ActivityChange.objects.create(organization=account.organization, account=account, **change)


def add_dummy_collars(account):
    print('...adding dummy collar accounts and individuals')

    global_config = aws.get_global_config()
    species_subtypes = global_config['SPECIES_SUBTYPES']

    names = ['James', 'Casey', 'Crosby', 'Carly', 'Kevin',
             'Kenny', 'Elizabeth', 'Claire', 'Norman', 'Vladimir',
             'Tamara', 'Alex', 'Gaby', 'Malia', 'Hannah', 'Emma',
             'Bruce', 'Laura', 'Andrew', 'Ashley', 'Connor']

    specieses = ['elephant', 'giraffe', 'lion']
    providers = ['orbcomm', 'savannah_tracking']

    for i in range(random.randint(3, 6)):

        provider = random.choice(providers)
        species = random.choice(specieses).capitalize()
        title = f'{species} - Orbcomm' if provider == 'orbcomm' else f'{species} - Savannah Tracking'

        account_data = {
            'source': 'collar',
            'provider': provider,
            'type': species,
            'title': title,
            'outputs': json.dumps({
                'output_agol': True,
                'output_database': True,
                'output_kml': True
            })
        }

        try:
            account = RealTimeAccount.objects.create(organization=account.organization, **account_data)
        except:
            pass
        else:
            # add individuals
            for i in range(random.randint(5, 10)):

                subtype = random.choice(species_subtypes[account.type]) if account.type in species_subtypes.keys() else None

                individual = {
                    'account': account,
                    'device_id': str(uuid.uuid4()).split('-')[0],
                    'status': random.choice(constants.INDIVIDUAL_STATUSES)[0],
                    'name': random.choice(names),
                    'subtype': subtype,
                    'sex': random.choice(constants.SEXES)[0],
                    'datetime_last_position': timezone.now() - datetime.timedelta(hours=random.randint(0, 36))
                }

                RealTimeIndividual.objects.create(**individual)





# add dummy drives or only stuff that user can't receive anonymous data?

def add_dummy_radios(account):
    print('...adding dummy radios')



def clear_all_content():
    print("...clearing all content")
    ActivityAlert.objects.all().delete()
    ActivityChange.objects.all().delete()
    DriveFileAccount.objects.all().delete()
    RealTimePosition.objects.all().delete()
    RealTimePositionHash.objects.all().delete()
    RealTimeIndividual.objects.all().delete()
    RealTimeAccount.objects.all().delete()
    Account.objects.all().delete()
    Organization.objects.all().delete()

    cognito.remove_all_users()


