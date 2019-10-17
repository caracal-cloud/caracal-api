
from django.conf import settings
from django.contrib.gis.db import models
import uuid

from account.models import Organization
from caracal.common import constants
from caracal.common.models import BaseAsset, get_utc_datetime_now


# Network of Jackal Phones - just one per organization

class Network(BaseAsset):

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='jackal_network')
    write_key = models.CharField(max_length=100, editable=False)


# Individual Jackal Phone

class Phone(BaseAsset):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='phones')
    device_id = models.CharField(max_length=200) # device specific id

    status = models.CharField(choices=constants.JACKAL_PHONE_STATUSES, max_length=50, default='pending')
    name = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    mark = models.CharField(max_length=100, blank=True, null=True)
    phone_numbers = models.CharField(max_length=255, blank=True, null=True) # phone numbers json list

    class Meta:
        ordering = ['-datetime_created']
        unique_together = ['network', 'device_id']

# Recordings

class BaseJackalRecording(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=get_utc_datetime_now)
    datetime_recorded = models.DateTimeField()

    class Meta:
        abstract = True


class Call(BaseJackalRecording):

    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='calls')
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='calls')

    is_sent = models.BooleanField() # was this text sent by the phone
    other_phone_number = models.CharField(max_length=50)
    duration_secs = models.IntegerField()

    class Meta:
        unique_together = ['phone', 'datetime_recorded', 'is_sent', 'other_phone_number', 'duration_secs']


class Contact(BaseJackalRecording):

    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='contacts')
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='contacts')

    name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=50)

    class Meta:
        unique_together = ['phone', 'name', 'phone_number']


class Location(BaseJackalRecording):

    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='locations')
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='locations')

    position = models.PointField(srid=settings.SRID, null=False)
    accuracy_m = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['phone', 'datetime_recorded', 'position', 'accuracy_m']


class Text(BaseJackalRecording):

    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='texts')
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='texts')

    is_sent = models.BooleanField() # was this text sent by the phone
    other_phone_number = models.CharField(max_length=50)
    message = models.TextField(blank=True) # can add translations later

    class Meta:
        unique_together = ['phone', 'datetime_recorded', 'is_sent', 'other_phone_number', 'message']
