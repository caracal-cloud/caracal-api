
from django.conf import settings

from activity.models import ActivityAlert, ActivityChange
from account.models import Account, Organization
from auth import cognito

from caracal.common.models import RealTimeAccount, RealTimeIndividual, RealTimePosition, RealTimePositionHash


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


def clear_all_content():
    print("...clearing all content")
    ActivityAlert.objects.all().delete()
    ActivityChange.objects.all().delete()
    RealTimePosition.objects.all().delete()
    RealTimePositionHash.objects.all().delete()
    RealTimeIndividual.objects.all().delete()
    RealTimeAccount.objects.all().delete()
    Account.objects.all().delete()
    Organization.objects.all().delete()

    cognito.remove_all_users()


