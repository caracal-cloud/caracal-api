from django.db import models

from account.models import Organization
from caracal.common import constants
from caracal.common.models import BaseAsset, RealTimeAccount
from drives.models import DriveFileAccount


class DataConnection(BaseAsset):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    # Input - only one will be non-null
    realtime_account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, null=True, related_name='connections')
    realtime_alert = models.ForeignKey('RealtimeAlert', on_delete=models.CASCADE, null=True, related_name='connections')
    drive_account = models.ForeignKey(DriveFileAccount, on_delete=models.CASCADE, null=True, related_name='connections')

    output = models.ForeignKey('DataOutput', on_delete=models.CASCADE, null=True)

    def __str__(self):
        if self.realtime_account:
            source = 'rt account'
        elif self.realtime_alert:
            source = 'rt alert'
        else:
            source = 'drive account'
        return f'{self.organization.name} - {source} - {self.output.type}'


class DataOutput(BaseAsset):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    type = models.CharField(choices=constants.OUTPUT_TYPES, max_length=50, blank=False, null=False)

    status = models.CharField(choices=constants.OUTPUT_STATUSES, max_length=50, default='pending', blank=False, null=False)

    def __str__(self):
        return f'{self.organization.name} - {self.type} - {self.status}'


class RealtimeAlert(BaseAsset):

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

