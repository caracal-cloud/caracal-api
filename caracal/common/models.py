
from django.conf import settings
from django.contrib.gis.db import models
from django.utils import timezone
import uuid

from caracal.common import constants


class BaseAsset(models.Model):

    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class RealTimeAccount(BaseAsset):

    status = models.CharField(choices=constants.ACCOUNT_STATUSES, max_length=50, default='pending')

    class Meta:
        app_label = 'account'


class RealTimeIndividual(BaseAsset):

    account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, related_name="realtime_individuals")
    device_id = models.CharField(max_length=100) # provider specific ID

    # metrics
    monthly_paths = models.TextField(null=True)
    last_position = models.PointField(srid=settings.SRID, null=True)
    datetime_last_position = models.DateTimeField(null=True)

    class Meta:
        app_label = 'account'
        unique_together = ['account', 'device_id']


class RealTimePosition(BaseAsset):

    account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_related")
    individual = models.ForeignKey(RealTimeIndividual, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_related")

    position = models.PointField(srid=settings.SRID, null=False)
    datetime_recorded = models.DateTimeField(null=True)
    temp_celcius = models.DecimalField(max_digits=5, decimal_places=1, null=True)

    class Meta:
        app_label = 'account'
        unique_together = ['individual', 'position', 'datetime_recorded']


class RealTimePositionHash(models.Model):

    datetime_created = models.DateTimeField(default=timezone.now)
    account = models.ForeignKey(RealTimeAccount, on_delete=models.CASCADE, related_name='hash_positions')
    hash = models.CharField(max_length=255, unique=True)

    class Meta:
        app_label = 'account'





























