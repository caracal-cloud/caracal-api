from django.db import models

from account.models import Organization
from caracal.common import constants
from caracal.common.models import BaseAsset, RealTimeAccount
from drives.models import DriveFileAccount


class DataConnection(BaseAsset):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    # Input - only one will be non-null
    realtime_account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, null=True)
    drive_account = models.ForeignKey(DriveFileAccount, on_delete=models.CASCADE, null=True)

    output = models.ForeignKey('DataOutput', on_delete=models.CASCADE, null=True)


class DataOutput(BaseAsset):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    type = models.CharField(choices=constants.OUTPUT_TYPES, max_length=50, blank=False, null=False)

    status = models.CharField(choices=constants.OUTPUT_STATUSES, max_length=50, default='pending', blank=False, null=False)


class RealtimeAlert(BaseAsset):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    realtime_account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE)

    # Recipients
    emails = models.TextField(blank=True, null=True) # json encoded list, email recipients
    phone_numbers = models.TextField(blank=True, null=True) # json encoded list, SMS recipients

    # Fleeing
    max_daily_distance_km = models.IntegerField(null=True) # max distance an individual can travel in a day before sending alert
    max_weekly_distance_km = models.IntegerField(null=True) # max distance an individual can travel in a week before sending alert

    # Immobility - if individual has traveled less than immobility_distance_m in immobility_wait_min then send alert
    immobility_wait_min = models.IntegerField(null=True) # time to wait for an immobile individual before sending alert
    immobility_distance_m = models.IntegerField(null=True) # distance threshold individual must pass in wait min to not send alert

