
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

    def __str__(self):
        return f'{self.device_id}, {self.name}'


# Phone Contacted by Jackal Phone

class OtherPhone(BaseAsset):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='other_phones')
    phone_number = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    mark = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['name', 'phone_number']
        unique_together = ['network', 'phone_number']

    def __str__(self):
        return f'{self.phone_number}, {self.name}'

# Recordings

class BaseJackalRecording(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=get_utc_datetime_now)
    datetime_recorded = models.DateTimeField()

    class Meta:
        abstract = True


class Call(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='calls')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='calls')
    other_phone = models.ForeignKey(OtherPhone, on_delete=models.CASCADE, related_name='calls')

    is_sent = models.BooleanField() # was this text sent by the phone
    duration_secs = models.IntegerField()

    class Meta:
        unique_together = ['phone', 'other_phone', 'datetime_recorded', 'is_sent', 'duration_secs']


class Contact(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='contacts')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='contacts')
    other_phone = models.ForeignKey(OtherPhone, on_delete=models.CASCADE, related_name='contacts')

    class Meta:
        unique_together = ['phone', 'other_phone']


class Location(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='locations')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='locations')

    position = models.PointField(srid=settings.SRID, null=False)
    accuracy_m = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['phone', 'datetime_recorded', 'position', 'accuracy_m']


class Text(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='texts')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='texts')
    other_phone = models.ForeignKey(OtherPhone, on_delete=models.CASCADE, related_name='texts')

    is_sent = models.BooleanField() # was this text sent by the phone
    message = models.TextField(blank=True) # can add translations later

    class Meta:
        unique_together = ['phone', 'other_phone', 'datetime_recorded', 'is_sent', 'message']
