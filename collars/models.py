
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

from account.models import Organization

class CollarProvider(models.Model):
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    name = models.CharField(max_length=200, null=False, blank=False) # i.e. Savannah Tracker
    short_name = models.CharField(max_length=200, null=False, blank=False) # i.e. savannah
    base_url = models.CharField(max_length=200, null=False, blank=False)
    is_available = models.BooleanField(default=False) # user can use this provider


class CollarAccount(models.Model):
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    provider_short_name = models.CharField(max_length=100)
    species = models.CharField(max_length=100)
    # Orbcomm
    timezone= models.CharField(max_length=20, null=True, blank=True)
    company_id = models.CharField(max_length=50, null=True, blank=True)
    # Savannah Tracker
    username = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True)

    def validate_unique(self, exclude=None):
        if self.provider_short_name == 'orbcomm':
            a = CollarAccount.objects.filter(organization=self.organization,
                                             provider_short_name=self.provider_short_name,
                                             species=self.species,
                                             timezone=self.timezone,
                                             company_id=self.company_id)
            if a.count() > 0:
                raise ValidationError('orbcomm uniqueness on name, species, timezone and company_id')
        elif self.provider_short_name == 'savannah':
            a = CollarAccount.objects.filter(organization=self.organization,
                                             provider_short_name=self.provider_short_name,
                                             species=self.species,
                                             username=self.username,
                                             password=self.password)
            if a.count() > 0:
                raise ValidationError('savannah uniqueness on name, species, username and password')

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(CollarAccount, self).save(*args, **kwargs)



class CollarIndividual(models.Model):
    # todo: this will be added by a lambda function... and modified through this app
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    account = models.ForeignKey(CollarAccount, on_delete=models.CASCADE)

    collar_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    sex = models.CharField(max_length=100) # enum?
    type = models.CharField(max_length=100)
    status = models.CharField(max_length=100) # enum?


class CollarPosition(models.Model):
    # todo: this will be added by a lambda function, and accessed by a lambda function (output function)
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_recorded = models.DateTimeField(null=True)

    individual = models.ForeignKey(CollarIndividual, on_delete=models.CASCADE)

    position = models.PointField()




