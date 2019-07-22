
from django.contrib.gis.db import models
from django.utils import timezone
import uuid

from account.models import Account, Organization
from caracal.common import constants
from caracal.common.models import BaseAccount, BaseAsset


class DriveFileAccount(BaseAsset, BaseAccount):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='drive_files')

    provider = models.CharField(choices=constants.DRIVE_PROVIDERS, max_length=100)
    file_type = models.CharField(choices=constants.DRIVE_FILETYPES, max_length=50)
    file_id = models.CharField(max_length=250)

    # spreadsheets
    sheet_ids = models.CharField(max_length=250, default='*') # * means all
    header_row_index = models.IntegerField(default=0)
    coordinate_system = models.CharField(max_length=50, choices=constants.COORDINATE_SYSTEMS, default='decimal degrees')

    class Meta:
        ordering = ['-datetime_created']
        #unique_together = ['organization', 'file_id']
