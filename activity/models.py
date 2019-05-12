
from django.contrib.gis.db import models
from django.utils import timezone
import uuid

from account.models import Account, Organization
from caracal.common import constants
from collars.models import CollarAccount


class ActivityAlert(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='alerts')

    # feedback = models.CharField(constants.ALERT_FEEDBACK, blank=True, null=True)
    level = models.CharField(choices=constants.ALERT_LEVELS, max_length=50)
    message = models.CharField(max_length=200)

    class Meta:
        ordering = ['-datetime_created']


class ActivityChange(models.Model):
    # user 1 added elephant account, user 2 dismissed an alert (no elephant positions)

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='changes')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='changes')

    message = models.CharField(max_length=200)

    class Meta:
        ordering = ['-datetime_created']