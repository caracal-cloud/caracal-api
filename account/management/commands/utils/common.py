
from django.conf import settings

from activity.models import ActivityAlert, ActivityChange
from account.models import Account, Organization
from auth import cognito

from caracal.common.models import RealTimeAccount, RealTimeIndividual, RealTimePosition, RealTimePositionHash


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


