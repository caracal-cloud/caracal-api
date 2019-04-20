
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

from account.models import Account, Organization
from caracal.common import constants


class CollarProvider(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    name = models.CharField(max_length=200, null=False, blank=False) # i.e. Savannah Tracking
    short_name = models.CharField(max_length=200, null=False, blank=False) # i.e. savannah
    base_url = models.CharField(max_length=200, null=False, blank=False)
    is_available = models.BooleanField(default=False) # user can use this provider

    class Meta:
        unique_together = ['name', 'short_name', 'base_url']


class CollarAccount(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    provider = models.ForeignKey(CollarProvider, on_delete=models.CASCADE, related_name='collar_accounts')
    species = models.CharField(max_length=100)

    orbcomm_timezone = models.CharField(max_length=20, null=True, blank=True)
    orbcomm_company_id = models.CharField(max_length=50, null=True, blank=True)
    savannah_tracking_username = models.CharField(max_length=100, null=True, blank=True)
    savannah_tracking_password = models.CharField(max_length=100, null=True, blank=True)

    def validate_unique(self, exclude=None):
        if self.provider.short_name == 'orbcomm':
            a = CollarAccount.objects.filter(organization=self.organization,
                                             provider__short_name=self.provider.short_name,
                                             species=self.species,
                                             orbcomm_timezone=self.orbcomm_timezone,
                                             orbcomm_company_id=self.orbcomm_company_id)
            if a.count() > 0:
                raise ValidationError('orbcomm uniqueness on name, species, orbcomm_timezone and orbcomm_company_id')
        elif self.provider.short_name == 'savannah_tracking':
            a = CollarAccount.objects.filter(organization=self.organization,
                                             provider__short_name=self.provider.short_name,
                                             species=self.species,
                                             savannah_tracking_username=self.savannah_tracking_username,
                                             savannah_tracking_password=self.savannah_tracking_password)
            if a.count() > 0:
                raise ValidationError('savannah uniqueness on name, species, username and password')

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(CollarAccount, self).save(*args, **kwargs)

    class Meta:
        ordering = ['provider__name', '-datetime_created']


class CollarAccountActivity(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)

    user_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='collar_account_activities')
    collar_account = models.ForeignKey(CollarAccount, on_delete=models.CASCADE, related_name='collar_account_activities')
    action = models.CharField(choices=constants.COLLAR_ACCOUNT_ACTIVITIES, max_length=100)


class CollarIndividual(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    collar_account = models.ForeignKey(CollarAccount, on_delete=models.CASCADE, related_name='collar_individuals')
    collar_id = models.CharField(max_length=100) # provider specific ID

    name = models.CharField(max_length=100, null=True, blank=True)
    sex = models.CharField(choices=constants.SEXES, max_length=100, null=True, blank=True) # enum?
    subtype = models.CharField(max_length=100, null=True, blank=True) # (i.e. forest, savannah) # todo: serve species/subspecies endpoint:)
    status = models.CharField(choices=constants.COLLAR_STATUSES, default='active', max_length=100, null=True, blank=True)

    def __str__(self):
        return "%s - %s - %s - %s" % (self.name, self.sex, self.subtype, self.status)

    class Meta:
        ordering = ['status', 'name']
        unique_together = ['collar_account', 'collar_id']


class CollarPosition(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)

    collar_account = models.ForeignKey(CollarAccount, on_delete=models.CASCADE, related_name='positions', null=False)
    individual = models.ForeignKey(CollarIndividual, on_delete=models.CASCADE, related_name='positions')

    datetime_recorded = models.DateTimeField(null=True)
    position = models.PointField(srid=settings.SRID, null=False)
    temperature = models.DecimalField(max_digits=5, decimal_places=1, null=True) # Celcius
    savannah_tracking_id = models.BigIntegerField(null=True)

    class Meta:
        unique_together = ['datetime_recorded', 'individual', 'position']

