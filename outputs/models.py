from django.db import models

from account.models import Account, Organization
from caracal.common import constants
from caracal.common.models import BaseAsset, RealTimeAccount
from custom_source.models import Source
from drives.models import DriveFileAccount


# TODO: FINISHING MODELING CONNECTIONS... custom source, remove output

class AgolAccount(BaseAsset):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='agol_accounts')
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='agol_account')

    oauth_access_token = models.TextField(blank=True, null=True)
    oauth_access_token_expiry = models.DateTimeField(blank=True, null=True)
    oauth_refresh_token = models.TextField(blank=True, null=True)
    group_id = models.CharField(max_length=255, blank=True, null=True)
    feature_service_url = models.CharField(max_length=200, blank=True, null=True)
    username = models.CharField(max_length=200, blank=True, null=True)


class DataConnection(BaseAsset):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='connections')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='connections', null=True)

    # Input - only one will be non-null
    custom_source = models.ForeignKey(Source, on_delete=models.CASCADE, null=True, related_name='connections')
    drive_account = models.ForeignKey(DriveFileAccount, on_delete=models.CASCADE, null=True, related_name='connections')
    realtime_account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, null=True, related_name='connections')

    # Output - only one will be non-null
    agol_account = models.ForeignKey(AgolAccount, on_delete=models.CASCADE, null=True, related_name='connections')

    def __str__(self):
        if self.realtime_account:
            source = 'realtime 3p'
        elif self.custom_source:
            source = 'realtime custom source'
        else:
            source = 'drive account'
        return f'{self.organization.name} - {source}'


class RealtimeAlert(BaseAsset):
    # not exactly an "output"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    realtime_account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE) # simplifies queries from account to alert

    # Recipients
    emails = models.TextField(blank=True, null=True) # json encoded list, email recipients
    phone_numbers = models.TextField(blank=True, null=True) # json encoded list, SMS recipients

    # Fleeing
    max_daily_distance_km = models.IntegerField(null=True) # max distance an individual can travel in a day before sending alert
    max_weekly_distance_km = models.IntegerField(null=True) # max distance an individual can travel in a week before sending alert

    # Immobility - if individual has traveled less than immobility_distance_m in immobility_wait_min then send alert
    immobility_wait_min = models.IntegerField(null=True) # time to wait for an immobile individual before sending alert
    immobility_distance_m = models.IntegerField(null=True) # distance threshold individual must pass in wait min to not send alert

