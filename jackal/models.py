
from django.conf import settings
from django.contrib.gis.db import models
import uuid

from account.models import Organization
from caracal.common import constants
from caracal.common.models import BaseAsset, get_datetime_epoch_start, get_utc_datetime_now


# Network of Jackal Phones - just one per organization

class Network(BaseAsset):

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='jackal_network')
    write_key = models.CharField(max_length=100, editable=False) # unique = True?

    cloudwatch_update_kml_rule_names = models.TextField(default="", blank=True, null=True)

    def __str__(self):
        return f'{self.organization.name} - {self.organization.short_name}'


# Individual Jackal Phone

class Phone(BaseAsset):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='phones')
    device_id = models.CharField(max_length=200) # device specific id

    datetime_last_update = models.DateTimeField(default=get_datetime_epoch_start)
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


class OtherPhone(BaseAsset):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='other_phones')
    phone_number = models.CharField(max_length=30)
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
        ordering = ['-datetime_recorded']
        unique_together = ['phone', 'other_phone', 'datetime_recorded', 'is_sent', 'duration_secs']


class Contact(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='contacts')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='contacts')
    other_phone = models.ForeignKey(OtherPhone, on_delete=models.CASCADE, related_name='contacts')

    class Meta:
        ordering = ['-datetime_recorded']
        unique_together = ['phone', 'other_phone']


class Location(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='locations')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='locations')

    position = models.PointField(srid=settings.SRID, null=False)
    accuracy_m = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-datetime_recorded']
        unique_together = ['phone', 'datetime_recorded', 'position', 'accuracy_m']


class Log(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='logs')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='logs')

    level = models.CharField(max_length=50) # info, warning, error
    message = models.TextField()

    class Meta:
        ordering = ['-datetime_recorded']


class Text(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='texts')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='texts')
    other_phone = models.ForeignKey(OtherPhone, on_delete=models.CASCADE, related_name='texts')

    is_sent = models.BooleanField() # was this text sent by the phone
    message = models.TextField(blank=True) # can add translations later

    class Meta:
        ordering = ['-datetime_recorded']
        unique_together = ['phone', 'other_phone', 'datetime_recorded', 'is_sent', 'message']


class WhatsAppCall(BaseJackalRecording):

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='whatsapp_calls')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='whatsapp_calls')
    whatsapp_user = models.ForeignKey('WhatsAppUser', on_delete=models.CASCADE, related_name='whatsapp_calls')

    call_log_id = models.IntegerField()
    duration_secs = models.IntegerField()
    from_me = models.BooleanField()

    class Meta:
        ordering = ['-datetime_created']
        unique_together = ['datetime_recorded', 'whatsapp_user', 'call_log_id', 'duration_secs']


class WhatsAppGroup(models.Model):
    
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=get_utc_datetime_now)

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='whatsapp_groups')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='whatsapp_groups')

    jid_id = models.IntegerField()
    user_string = models.CharField(max_length=200)

    subject = models.CharField(max_length=200, blank=True, null=True) # the name of the group

    class Meta:
        ordering = ['-datetime_created']
        unique_together = ['phone', 'user_string']

    def __str__(self):
        return f"{self.subject} - {self.user_string}"


class WhatsAppMessage(BaseJackalRecording):
    """
    1. from target to individual (jid_id not null, group_jid_id is null, from_me is True)
    2. to target from individual (jid_id not null, group_jid_id is null, from_me is False)
    3. from target to group (jid_id is null, group_jid_id not null, from_me is True)
    4. from individual to group (jid_id not null, group_jid_id not null, from_me is False)
    """

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='whatsapp_messages')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='whatsapp_messages')
    whatsapp_user = models.ForeignKey('WhatsAppUser', on_delete=models.CASCADE, related_name='whatsapp_messages', null=True)
    whatsapp_group = models.ForeignKey(WhatsAppGroup, on_delete=models.CASCADE, related_name='whatsapp_messages', null=True)

    from_me = models.BooleanField()
    media_url = models.TextField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    messages_id = models.IntegerField()

    class Meta:
        unique_together = ['phone', 'datetime_recorded', 'message', 'from_me']


class WhatsAppUser(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=get_utc_datetime_now)

    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name='whatsapp_users')
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name='whatsapp_users')
    groups = models.ManyToManyField(WhatsAppGroup)

    jid_id = models.IntegerField()
    user_string = models.CharField(max_length=200)

    class Meta:
        unique_together = ['phone', 'user_string']

    def __str__(self):
        return f"{self.user_string} - {self.jid_id}"

    