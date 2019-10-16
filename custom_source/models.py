
from datetime import datetime, timezone
from django.conf import settings
from django.contrib.gis.db import models
import uuid

from account.models import Account, Organization
from caracal.common.models import BaseAsset, get_utc_datetime_now

# Source -> Device -> Record

class Device(BaseAsset):

    source = models.ForeignKey('Source', on_delete=models.CASCADE)

    device_id = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-datetime_created']

    def __str__(self):
        return f'{self.device_id} - {self.name}'


class Record(models.Model):

    # house keeping
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=get_utc_datetime_now)
    source = models.ForeignKey('Source', on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, null=True) # remove null?

    # where and when
    position = models.PointField(srid=settings.SRID, null=False) # fixme: allow to specify srid
    datetime_recorded = models.DateTimeField(null=True)

    # optional
    alt_m = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    speed_kmh = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    temp_c = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    class Meta:
        ordering = ['-datetime_created']

    def __str__(self):
        return f'{self.position}'


class Source(BaseAsset):

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='custom_sources')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='custom_sources')

    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True, null=True)
    write_key = models.CharField(max_length=100)

    cloudwatch_get_data_rule_name = models.CharField(max_length=200, blank=True, null=True)
    cloudwatch_update_kml_rule_names = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-datetime_created']

    def __str__(self):
        return f'{self.name}'
