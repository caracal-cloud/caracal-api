
from django.contrib.gis.db import models
from django.utils import timezone
import uuid

from account.models import Account, Organization
from caracal.common import constants
from caracal.common.models import BaseAsset


class GoogleSheetsAccount(BaseAsset):

    # generic account fields
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='google_sheet_accounts')
    status = models.CharField(choices=constants.ACCOUNT_STATUSES, max_length=50, default='pending')
    title = models.CharField(max_length=100, blank=True, null=True)
    outputs = models.TextField(blank=False, null=True) # outputs as json

    # google sheets specific stuff
    file_id = models.CharField(max_length=250)
    sheet_ids = models.CharField(max_length=250, default='*') # * means all
    header_row_index = models.IntegerField(default=0)
    coordinate_system = models.CharField(max_length=50, choices=constants.COORDINATE_SYSTEMS, default='decimal degrees')

    class Meta:
        ordering = ['-datetime_created']
        unique_together = ['organization', 'file_id']
