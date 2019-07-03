
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

from account.models import Account, Organization
from caracal.common import constants
import caracal.common.models as parent_models



"""

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

    def __str__(self):
        return f'{self.name} - {self.short_name}'

    class Meta:
        unique_together = ['name', 'short_name', 'base_url']


class CollarAccount(parent_models.RealTimeAccount):

    collar_account_uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='collar_accounts')
    provider = models.ForeignKey(CollarProvider, on_delete=models.CASCADE, related_name='collar_accounts')
    species = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True, null=True)

    #orbcomm_timezone = models.CharField(max_length=20, null=True, blank=True)
    #orbcomm_company_id = models.CharField(max_length=50, null=True, blank=True)
    #savannah_tracking_username = models.CharField(max_length=100, null=True, blank=True)
    #savannah_tracking_password = models.CharField(max_length=100, null=True, blank=True)
    savannah_tracking_record_indexes = models.TextField(blank=True, null=True) # last position indexes json

    account_ptr = models.OneToOneField(
        parent_models.RealTimeAccount, on_delete=models.CASCADE,
        parent_link=True,
        related_name='collar_account'
    )

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
        self.validate_unique() # fixme: this breaks when trying to update an account...
        super(CollarAccount, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.species} - {self.provider.short_name} - {self.organization.short_name}'

    class Meta:
        ordering = ['provider__name', '-datetime_created']


class CollarIndividual(parent_models.RealTimeIndividual):

    collar_individual_uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    collar_account = models.ForeignKey(CollarAccount, on_delete=models.CASCADE, related_name='collar_individuals')

    name = models.CharField(max_length=100, null=True, blank=True)
    sex = models.CharField(choices=constants.SEXES, max_length=100, null=True, blank=True) # enum?
    subtype = models.CharField(max_length=100, null=True, blank=True) # (i.e. forest, savannah) # todo: serve species/subspecies endpoint:)
    status = models.CharField(choices=constants.COLLAR_STATUSES, default='active', max_length=100, null=True, blank=True)

    individual_ptr = models.OneToOneField(
        parent_models.RealTimeIndividual, on_delete=models.CASCADE,
        parent_link=True,
        related_name='collar_individual'
    )

    def __str__(self):
        return "%s - %s - %s - %s" % (self.name, self.sex, self.subtype, self.status)

    class Meta:
        ordering = ['status', 'name']


class OrbcommCollarPosition(parent_models.RealTimePosition):

    position_ptr = models.OneToOneField(
        parent_models.RealTimePosition, on_delete=models.CASCADE,
        parent_link=True,
        related_name='orbcomm_collar_position'
    )


class SavannahTrackingCollarPosition(parent_models.RealTimePosition):

    savannah_tracking_id = models.BigIntegerField(null=False, default=-1)
    position_ptr = models.OneToOneField(
        parent_models.RealTimePosition, on_delete=models.CASCADE,
        parent_link=True,
        related_name='savannah_tracking_collar_position'
    )

"""

