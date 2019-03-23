
from django.contrib.gis.db import models
from django.utils import timezone
import uuid


class CollarAccount(models.Model):
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_updated = models.DateTimeField(null=True)
    datetime_deleted = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)

    provider_name = models.CharField(max_length=100)
    species = models.CharField(max_length=100)
    # Orbcomm
    timezone= models.CharField(max_length=20, null=True, blank=True)
    company_id = models.CharField(max_length=50, null=True, blank=True)
    # Savannah Tracker
    username = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True)


class CollarIndividual(models.Model):
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
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = models.DateTimeField(default=timezone.now)
    datetime_recorded = models.DateTimeField(null=True)

    individual = models.ForeignKey(CollarIndividual, on_delete=models.CASCADE)

    position = models.PointField()




