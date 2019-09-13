
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
from outputs.models import DataConnection, DataOutput


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
        },
        {
            'message': 'Martin Ishimwe edited elephant Julie'
        },
        {
            'message': 'Roger Green edited radio C50'
        }
    ]

    for change in changes:
        ActivityChange.objects.create(organization=account.organization, account=account, **change)


def add_dummy_collars(account):
    print('...adding dummy collar accounts and individuals')

    organization = account.organization

    global_config = aws.get_global_config()
    species_subtypes = global_config['SPECIES_SUBTYPES']

    names = ['James', 'Casey', 'Crosby', 'Carly', 'Kevin',
             'Kenny', 'Elizabeth', 'Claire', 'Norman', 'Vladimir',
             'Tamara', 'Alex', 'Gaby', 'Malia', 'Hannah', 'Emma',
             'Bruce', 'Laura', 'Andrew', 'Ashley', 'Connor']

    specieses = ['elephant', 'giraffe', 'lion'] # weird name intentional
    providers = ['orbcomm', 'savannah_tracking']

    for i in range(random.randint(4, 7)):

        provider = random.choice(providers)
        species = random.choice(specieses).capitalize()
        title = f'{species} - Orbcomm' if provider == 'orbcomm' else f'{species} - Savannah Tracking'

        outputs = {
            'output_agol': True,
            'output_database': True,
            'output_kml': True
        }

        account_data = {
            'source': 'collar',
            'provider': provider,
            'type': species,
            'title': title,
            'outputs': json.dumps(outputs)
        }

        try:
            account = RealTimeAccount.objects.create(organization=organization, **account_data)
        except:
            pass
        else:
            # add individuals
            for i in range(random.randint(7, 12)):

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

        # setup connections and outputs
        output_types = [output[0] for output in constants.OUTPUT_TYPES]
        for output_type in output_types:
            if output_type in outputs.keys() and outputs[output_type]:
                try:
                    output = DataOutput.objects.get(organization=organization, type=output_type)
                except DataOutput.DoesNotExist:
                    output = DataOutput.objects.create(organization=organization, type=output_type)

                DataConnection.objects.create(organization=organization, realtime_account=account, output=output)


# add dummy drives or only stuff that user can't receive anonymous data?

def add_dummy_radios(account):
    print('...adding dummy radios')

    names = ['Jonie', 'Mitchel', 'Bill', 'Jerry', 'Mick',
             'Keith', 'Ronnie', 'Tobias', 'Jed', 'Alfred',
             'Katherine', 'Monique', 'Thor', 'Robin', 'Isaac', 'Louis',
             'Xenu', 'Webster', 'Quora', 'Bright', 'Rachel']

    providers = ['trbonet']

    for i in range(random.randint(3, 6)):

        provider = random.choice(providers)
        title = f'Radios - {provider}'

        account_data = {
            'source': 'radio',
            'provider': provider,
            'type': str(uuid.uuid4()),
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
            for i in range(random.randint(7, 12)):

                individual = {
                    'account': account,
                    'device_id': str(uuid.uuid4()).split('-')[0],
                    'status': random.choice(constants.INDIVIDUAL_STATUSES)[0],
                    'name': random.choice(names),
                    'subtype': 'staff',
                    'sex': random.choice(constants.SEXES)[0],
                    'blood_type': random.choice(constants.BLOOD_TYPES)[0],
                    'call_sign': f'{chr(random.randint(65, 90))}{random.randint(10, 99)}',
                    'datetime_last_position': timezone.now() - datetime.timedelta(hours=random.randint(0, 36)),
                    'phone_number': f'+{random.randint(1, 255)}{random.randint(100000, 999999)}'
                }

                RealTimeIndividual.objects.create(**individual)



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


def clear_dummy_content(account):
    print("...clearing all content")
    ActivityAlert.objects.filter(organization=account.organization).delete()
    ActivityChange.objects.filter(account=account).delete()
    DriveFileAccount.objects.filter(organization=account.organization).delete()
    RealTimePosition.objects.filter(account__organization=account.organization).delete()
    RealTimePositionHash.objects.filter(account__organization=account.organization).delete()
    RealTimeIndividual.objects.filter(account__organization=account.organization).delete()
    RealTimeAccount.objects.filter(organization=account.organization).delete()
