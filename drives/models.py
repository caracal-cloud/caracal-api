
from django.contrib.gis.db import models
from django.utils import timezone
import uuid

from account.models import Account, Organization
from caracal.common import constants
from caracal.common.models import BaseAsset


class GoogleSheetsDocument(BaseAsset):

    title = models.CharField(max_length=50, blank=True, null=True)
    # doc id? header info, coords pos