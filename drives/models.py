
from django.contrib.gis.db import models

from account.models import Account, Organization
from caracal.common import constants
from caracal.common.models import BaseAccount, BaseAsset


class DriveFileAccount(BaseAsset, BaseAccount):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='drive_files')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='drive_files', null=True)

    provider = models.CharField(choices=constants.DRIVE_PROVIDERS, max_length=100)
    file_type = models.CharField(choices=constants.DRIVE_FILETYPES, max_length=50)
    file_id = models.CharField(max_length=250)
    sheet_ids = models.CharField(max_length=250, default='*') # json list

    # configuration
    header_row_index = models.IntegerField(default=0)
    coordinate_system = models.CharField(max_length=50, choices=constants.COORDINATE_SYSTEMS, default='decimal degrees')
    x_column_index = models.IntegerField() # longitude, easting
    y_column_index = models.IntegerField() # latitude, northing
    grid_zone_column_index = models.IntegerField(null=True) # utm ex. 35N, 35M
    date_column_index = models.IntegerField(null=True)

    # Google
    google_oauth_access_token = models.TextField(null=True)
    google_oauth_refresh_token = models.TextField(null=True)
    google_oauth_access_token_expiry = models.DateTimeField(null=True) # UTC

    # Data and scheduling
    cloudwatch_get_data_rule_name = models.CharField(max_length=200, blank=True, null=True)
    cloudwatch_update_kml_rule_names = models.TextField(default="", blank=True, null=True) # multiple rules
    most_recent_s3_object_key = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        ordering = ['-datetime_created']
        #unique_together = ['organization', 'file_id']
