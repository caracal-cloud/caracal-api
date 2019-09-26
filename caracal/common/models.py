
from datetime import datetime, timezone
from django.conf import settings
from django.contrib.gis.db import models
import uuid

from account.models import Organization
from caracal.common import constants


def get_num_sources(organization):

    num_sources = organization.rt_accounts.filter(is_active=True).count() + \
                  organization.drive_files.filter(is_active=True).count() + \
                  organization.custom_sources.filter(is_active=True).count()
    return num_sources


def get_utc_datetime_now():
    return datetime.utcnow().replace(tzinfo=timezone.utc)


class BaseAsset(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=get_utc_datetime_now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class BaseAccount(models.Model):

    status = models.CharField(choices=constants.ACCOUNT_STATUSES, max_length=50, default='pending')
    title = models.CharField(max_length=100, blank=True, null=True)
    outputs = models.TextField(blank=False, null=True) # outputs as json

    class Meta:
        abstract = True


class RealTimeAccount(BaseAsset, BaseAccount):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='rt_accounts')

    # real-time accounts specific
    source = models.CharField(choices=constants.RT_ACCOUNT_SOURCES, max_length=50, blank=False, null=False)
    provider = models.CharField(choices=constants.RT_ACCOUNT_PROVIDERS, max_length=100, blank=False, null=False) # orbcomm, trbonet
    type = models.CharField(max_length=100) # i.e. elephant, random string for radio
    device_indexes = models.TextField(blank=True, null=True) # last position indexes as json

    # ArcGIS Online
    agol_layer_id = models.CharField(max_length=100, null=True)

    # Caracal Sync
    is_synced = models.NullBooleanField(default=False) # has this account been paired with a Caracal Sync instance

    class Meta:
        app_label = 'account'
        ordering = ['-datetime_created']
        unique_together = ['organization', 'source', 'provider', 'type']

    def __str__(self):
        return f'{self.source} - {self.provider} - {self.type} - {self.title}'


class RealTimeIndividual(BaseAsset):

    account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, related_name="rt_individuals")

    device_id = models.CharField(max_length=100) # provider specific ID
    status = models.CharField(choices=constants.INDIVIDUAL_STATUSES, max_length=50, default='active')
    name = models.CharField(max_length=100, null=True, blank=True)
    subtype = models.CharField(max_length=100, null=True, blank=True) # i.e. forest, QRF

    # alive
    sex = models.CharField(choices=constants.SEXES, max_length=100, null=True, blank=True)

    # human
    blood_type = models.CharField(choices=constants.BLOOD_TYPES, max_length=100, null=True, blank=True)
    call_sign = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)

    # animal

    # metrics
    monthly_paths = models.TextField(blank=True, null=True)
    last_position = models.PointField(srid=settings.SRID, null=True)
    datetime_last_position = models.DateTimeField(null=True)

    class Meta:
        app_label = 'account'
        ordering = ['-datetime_created']
        unique_together = ['account', 'device_id']

    def __str__(self):
        return f'{self.account} - {self.device_id} - {self.name} - {self.subtype}'


class RealTimePosition(BaseAsset):

    account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, related_name="rt_positions")
    individual = models.ForeignKey(RealTimeIndividual, on_delete=models.CASCADE, related_name="rt_positions")

    position = models.PointField(srid=settings.SRID, null=False)
    datetime_recorded = models.DateTimeField(null=True)
    temp_c = models.DecimalField(max_digits=5, decimal_places=1, null=True)

    class Meta:
        app_label = 'account'
        unique_together = ['individual', 'position', 'datetime_recorded']


class RealTimePositionHash(models.Model):

    datetime_created = models.DateTimeField(default=get_utc_datetime_now)
    account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, related_name='rt_hash_positions')
    individual = models.ForeignKey(RealTimeIndividual, on_delete=models.CASCADE, related_name='rt_hash_positions', null=True)
    datetime_recorded = models.DateTimeField()
    hash = models.CharField(max_length=255, unique=True)

    class Meta:
        app_label = 'account'





























