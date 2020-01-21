from datetime import datetime, timezone
from django.conf import settings
import json
import requests
from rest_framework import status
from rest_framework.response import Response
import simple_arcgis_wrapper as saw

from caracal.common import google
from outputs.models import AgolAccount


AGOL_ROOT = "https://www.arcgis.com/sharing/rest"
X_MIN, Y_MIN, X_MAX, Y_MAX = -26, -35, 56, 39
WKID = 4326

CARACAL_SERVICE_NAME = "Caracal"
CARACAL_SERVICE_DESCRIPTION = "Caracal data integration outputs"


def create_custom_source_feature_layer(
    title, description, feature_service, agol_account
):

    fields = saw.fields.Fields()
    fields.add_field("Date", saw.fields.DateField)
    fields.add_field("DeviceId", saw.fields.StringField)
    fields.add_field("Name", saw.fields.StringField)
    fields.add_field("AltM", saw.fields.DoubleField)
    fields.add_field("SpeedKmh", saw.fields.DoubleField)
    fields.add_field("TempC", saw.fields.DoubleField)

    return _create_feature_layer(
        title, fields, feature_service, agol_account, description=description
    )


def create_drive_feature_layer(
    title, description, feature_service, agol_account, extra_fields=list()
):

    fields = saw.fields.Fields()
    for extra_field in extra_fields:
        fields.add_field(extra_field, saw.fields.StringField)

    return _create_feature_layer(
        title, fields, feature_service, agol_account, description=description
    )


def create_jackal_feature_layer(title, feature_service, agol_account):

    fields = saw.fields.Fields()
    fields.add_field("Date", saw.fields.DateField)
    fields.add_field("DeviceId", saw.fields.StringField)
    fields.add_field("Name", saw.fields.StringField)
    fields.add_field("AccuracyM", saw.fields.DoubleField)

    return _create_feature_layer(title, fields, feature_service, agol_account)


def create_realtime_feature_layer(title, feature_service, agol_account):

    fields = saw.fields.Fields()
    fields.add_field("Date", saw.fields.DateField)
    fields.add_field("DeviceId", saw.fields.StringField)
    fields.add_field("Type", saw.fields.StringField)
    fields.add_field("Name", saw.fields.StringField)
    fields.add_field("Sex", saw.fields.StringField)
    fields.add_field("Status", saw.fields.StringField)
    fields.add_field("Provider", saw.fields.StringField)

    return _create_feature_layer(title, fields, feature_service, agol_account)


def _create_feature_layer(title, fields, feature_service, agol_account, description=""):

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,
        refresh_token=agol_account.oauth_refresh_token,
        username=agol_account.username,
        client_id=settings.AGOL_CLIENT_ID,
    )

    feature_layer = arcgis.services.create_feature_layer(
        layer_type="point",
        name=title,
        description=description,
        feature_service_url=feature_service.url,
        fields=fields,
        x_min=X_MIN,
        y_min=Y_MIN,
        x_max=X_MAX,
        y_max=Y_MAX,
    )

    return feature_layer


def delete_feature_layers(layer_ids, feature_service_url, agol_account):

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,
        refresh_token=agol_account.oauth_refresh_token,
        username=agol_account.username,
        client_id=settings.AGOL_CLIENT_ID,
    )

    return arcgis.services.delete_feature_layers(layer_ids, feature_service_url)


def get_custom_source_features(device_id, layer_id, agol_account):
    "docs"

    out_fields = ["OBJECTID"]
    where = f"DeviceId = '{device_id}'"

    return _get_features(
        out_fields=out_fields, where=where, layer_id=layer_id, agol_account=agol_account
    )


def get_collar_features(device_id, layer_id, agol_account):
    "docs"

    out_fields = ["OBJECTID"]
    where = f"DeviceId = '{device_id}'"

    return _get_features(
        out_fields=out_fields, where=where, layer_id=layer_id, agol_account=agol_account
    )


def get_jackal_features(device_id, layer_id, agol_account):

    out_fields = ["OBJECTID"]
    where = f"DeviceId = '{device_id}'"

    return _get_features(
        out_fields=out_fields, where=where, layer_id=layer_id, agol_account=agol_account
    )


def _get_features(out_fields, where, layer_id, agol_account):

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,
        refresh_token=agol_account.oauth_refresh_token,
        username=agol_account.username,
        client_id=settings.AGOL_CLIENT_ID,
    )

    return arcgis.services.get_features(
        out_fields=out_fields,
        where=where,
        layer_id=layer_id,
        feature_service_url=agol_account.feature_service_url,
    )


def get_or_create_caracal_feature_service(agol_account):

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,
        refresh_token=agol_account.oauth_refresh_token,
        username=agol_account.username,
        client_id=settings.AGOL_CLIENT_ID,
    )

    feature_service = arcgis.services.get_feature_service(
        name=CARACAL_SERVICE_NAME, owner_username=agol_account.username
    )
    if feature_service is None:
        print("creating feature service")
        feature_service = arcgis.services.create_feature_service(
            CARACAL_SERVICE_NAME, CARACAL_SERVICE_DESCRIPTION
        )

    return feature_service


def is_account_connected(agol_account):
    "Uses a hack to see if account is connected by trying to refresh token."

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,
        refresh_token=agol_account.oauth_refresh_token,
        username=agol_account.username,
        client_id=settings.AGOL_CLIENT_ID,
    )

    return arcgis.requester._refresh_access_token()


def update_features(updates, layer_id, agol_account):
    "docs"

    # TODO: validate updates?

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,
        refresh_token=agol_account.oauth_refresh_token,
        username=agol_account.username,
        client_id=settings.AGOL_CLIENT_ID,
    )

    return arcgis.services.update_features(
        updates, layer_id, agol_account.feature_service_url
    )
