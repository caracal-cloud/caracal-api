
from django.conf import settings

from activity.models import ActivityAlert, ActivityChange
from account.models import Account, Organization
from auth import cognito
from collars.models import CollarAccount, CollarIndividual, CollarPosition, CollarProvider


def clear_all_content():
    print("...clearing all content")
    ActivityAlert.objects.all().delete()
    ActivityChange.objects.all().delete()
    CollarPosition.objects.all().delete()
    CollarIndividual.objects.all().delete()
    CollarAccount.objects.all().delete()
    CollarProvider.objects.all().delete()
    Account.objects.all().delete()
    Organization.objects.all().delete()

    cognito.remove_all_users()


def create_overlord():
    print("...creating overlord")
    user = Account.objects.create_superuser(settings.OVERLORD_EMAIL, settings.OVERLORD_PASSWORD)
    cognito.confirm_user(user.email)

