
from datetime import datetime, timezone
from django.conf import settings
import json
import requests
from rest_framework import status
from rest_framework.response import Response

from caracal.common import google
from outputs.models import AgolAccount


AGOL_ROOT = 'https://www.arcgis.com/sharing/rest'
X_MIN = -26
X_MAX = 56
Y_MIN = -35
Y_MAX = 39
WKID = 4326


def create_caracal_feature_service(username, access_token):

    create_service_url = f'{AGOL_ROOT}/content/users/{username}/createService'

    create_params = {
        "name": 'Caracal',
        "serviceDescription": 'Caracal data integration outputs',
        "hasStaticData": False
    }

    data = {
        'token': access_token,
        'f': 'json',
        'createParameters': json.dumps(create_params),
        'outputType': 'featureService'
    }

    res = requests.post(create_service_url, data=data)
    res_data = res.json()

    if res_data.get('success', False):
        return res_data['encodedServiceURL']


def get_caracal_feature_service_url(username, access_token):

    search_url = f'{AGOL_ROOT}/search'
    params = {
        'q': f'title: Caracal AND owner: {username} AND type: \"Feature Service\"',
        'token': access_token,
        'f': 'json'
    }

    res = requests.get(search_url, params=params)
    res_data = res.json()

    if len(res_data.get('results', [])) > 0:
        feature_service = res_data['results'][0]
        return feature_service['url']


def create_custom_source_layer(layer_name, description, feature_service_url, access_token):

    create_layer_url = feature_service_url.replace('/services/', '/admin/services/') + '/addToDefinition'

    addToDefinition = {
        "layers": [
            {
                "name": layer_name,
                "description": description,
                "type": "Feature Layer",
                "geometryType": "esriGeometryPoint",
                "extent": {
                    "type": "extent",
                    "xmin": X_MIN,
                    "ymin": Y_MIN,
                    "xmax": X_MAX,
                    "ymax": Y_MAX,
                    "spatialReference": {
                        "wkid": WKID
                    }
                },
                "objectIdField": "OBJECTID",
                "fields": custom_source_point_fields
            }
        ]
    }

    data = {
        'token': access_token,
        'f': 'json',
        'addToDefinition': json.dumps(addToDefinition),
        'outputType': 'featureService',
    }

    res = requests.post(create_layer_url, data=data)
    res_data = res.json()

    if res_data.get('success', False):
        return res_data['layers'][0]['id']


def create_drive_layers(drive_account, feature_service_url, agol_access_token):

    create_layer_url = feature_service_url.replace('/services/', '/admin/services/') + '/addToDefinition'

    sheet_id_to_layer_id = dict()

    if drive_account.provider == 'google':

        google.verify_google_access_token_valid(drive_account)
        google_access_token = drive_account.google_oauth_access_token
        if google_access_token is None:
            print('google_oauth_access_token is None')
            return

        if drive_account.file_type == 'google_sheet':

            sheet_ids = json.loads(drive_account.sheet_ids)
            for sheet_id in sheet_ids:

                sheet_name = google.get_sheet_name(sheet_id, drive_account.file_id, google_access_token)
                if sheet_name is None:
                    print('invalid sheet_id: ' + sheet_id)
                    continue

                extra_headers = google.get_extra_headers(sheet_name, drive_account, google_access_token)
                if extra_headers is None:
                    continue

                extra_fields = [
                    {
                        "name": extra_header.title().replace(' ', ''),
                        "type": "esriFieldTypeString",
                        "alias": extra_header.title().replace(' ', ''),
                        "sqlType": "sqlTypeNVarchar",
                        "nullable": True,
                        "editable": True,
                        "domain": None,
                        "defaultValue": None,
                        "length": 256
                    }

                    for extra_header in extra_headers
                ]

                addToDefinition = {
                    "layers": [
                        {
                            "name": f'{drive_account.title} - {sheet_name}',
                            "type": "Feature Layer",
                            "geometryType": "esriGeometryPoint",
                            "extent": {
                                "type": "extent",
                                "xmin": X_MIN,
                                "ymin": Y_MIN,
                                "xmax": X_MAX,
                                "ymax": Y_MAX,
                                "spatialReference": {
                                    "wkid": WKID
                                }
                            },
                            "objectIdField": "OBJECTID",
                            "fields": base_point_fields + extra_fields
                        }
                    ]
                }

                data = {
                    'token': agol_access_token,
                    'f': 'json',
                    'addToDefinition': json.dumps(addToDefinition),
                    'outputType': 'featureService',
                }

                res = requests.post(create_layer_url, data=data)
                res_data = res.json()

                if res_data.get('success', False):
                    layer_id = res_data['layers'][0]['id']
                    sheet_id_to_layer_id[sheet_id] = layer_id

    return sheet_id_to_layer_id


def create_realtime_layer(layer_name, feature_service_url, access_token):

    create_layer_url = feature_service_url.replace('/services/', '/admin/services/') + '/addToDefinition'

    addToDefinition = {
        "layers": [
            {
                "name": layer_name,
                "type": "Feature Layer",
                "geometryType": "esriGeometryPoint",
                "extent": {
                    "type": "extent",
                    "xmin": X_MIN,
                    "ymin": Y_MIN,
                    "xmax": X_MAX,
                    "ymax": Y_MAX,
                    "spatialReference": {
                        "wkid": WKID
                    }
                },
                "objectIdField": "OBJECTID",
                "fields": realtime_point_fields
            }
        ]
    }

    data = {
        'token': access_token,
        'f': 'json',
        'addToDefinition': json.dumps(addToDefinition),
        'outputType': 'featureService',
    }

    res = requests.post(create_layer_url, data=data)
    res_data = res.json()

    if res_data.get('success', False):
        return res_data['layers'][0]['id']


def delete_layers(layer_ids, feature_service_url, access_token):

    delete_layer_url = feature_service_url.replace('/services/', '/admin/services/') + '/deleteFromDefinition'

    layers = [{ 'id': f'{layer_id}' } for layer_id in layer_ids]

    deleteFromDefinition = {
        "layers": layers
    }

    data = {
        'token': access_token,
        'f': 'json',
        'deleteFromDefinition': json.dumps(deleteFromDefinition),
    }

    res = requests.post(delete_layer_url, data=data)
    res_data = res.json()

    return res_data.get('success', False)

def get_layer(layer_id, feature_service_url, access_token):

    if layer_id is None:
        return None

    params = {
        'token': access_token,
        'f': 'json'
    }

    res = requests.get(feature_service_url, params=params)
    res_data = res.json()

    for layer in res_data.get('layers', []):
        if layer['id'] == int(layer_id):
            return layer


def refresh_access_token(refresh_token):

    if refresh_token is None:
        return None

    url = f'{AGOL_ROOT}/oauth2/token'
    data = {
        'client_id': settings.AGOL_CLIENT_ID,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    res = requests.post(url, data=data)
    tokens = res.json()

    if 'error' in tokens.keys():
        return None
    else:
        return tokens['access_token']


def verify_access_token_valid(agol_account):

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    if agol_account.oauth_access_token_expiry <= now:
        agol_account.oauth_access_token = refresh_access_token(agol_account.oauth_refresh_token)
        agol_account.save()


def verify_agol_state_and_get_account(user):
    try:
        agol_account = user.agol_account
        verify_access_token_valid(agol_account)
        if get_caracal_feature_service_url(agol_account.username, agol_account.oauth_access_token) is None:
            return Response({
                'error': 'feature_service_required',
                'message': 'The Caracal feature service is missing. Reconnect to ArcGIS Online to initialize it.'
            }, status=status.HTTP_400_BAD_REQUEST)
    except AgolAccount.DoesNotExist:
        return Response({
            'error': 'agol_account_required',
            'message': 'ArcGIS Online account required'
        }, status=status.HTTP_400_BAD_REQUEST)
    else:
        return agol_account


def update_disconnected_layer_name(layer, feature_service_url, access_token):

    if layer is None:
        return False

    layer_id = layer['id']
    layer_name = layer['name'].strip()

    # if layer_name already ends in (disconnected) then ignore
    if layer_name.endswith('disconnected)'):
        return True

    update_layer_url = feature_service_url.replace('/services/', '/admin/services/') + f'/{layer_id}/updateDefinition'

    updateDefinition = {
        'name': f'{layer_name} (disconnected)'
    }

    data = {
        'updateDefinition': json.dumps(updateDefinition),
        'token': access_token,
        'f': 'json'
    }

    update_res = requests.post(update_layer_url, data=data)
    update_data = update_res.json()

    return 'success' in update_data.keys()

base_point_fields = [
    {
        "name": "OBJECTID",
        "type": "esriFieldTypeOID",
        "alias": "OBJECTID",
        "sqlType": "sqlTypeOther",
        "nullable": False,
        "editable": False,
        "domain": None,
        "defaultValue": None
    },
    {
        "name": "Date",
        "type": "esriFieldTypeDate",
        "alias": "Date",
        "sqlType": "sqlTypeNVarchar",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
        "length": 256
    },
    {
        "name": "DeviceId",
        "type": "esriFieldTypeString",
        "alias": "DeviceId",
        "sqlType": "sqlTypeNVarchar",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
        "length": 256
    }
]

custom_source_point_fields = base_point_fields + [
    {
        "name": "AltM",
        "type": "esriFieldTypeDouble",
        "alias": "AltM",
        "sqlType": "sqlTypeFloat",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
    },
    {
        "name": "SpeedKmh",
        "type": "esriFieldTypeDouble",
        "alias": "SpeedKmh",
        "sqlType": "sqlTypeFloat",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
    },
    {
        "name": "TempC",
        "type": "esriFieldTypeDouble",
        "alias": "TempC",
        "sqlType": "sqlTypeFloat",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
    }
]


realtime_point_fields = base_point_fields + [
    {
        "name": "Type",
        "type": "esriFieldTypeString",
        "alias": "Type",
        "sqlType": "sqlTypeNVarchar",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
        "length": 256
    },
    {
        "name": "Name",
        "type": "esriFieldTypeString",
        "alias": "Name",
        "sqlType": "sqlTypeNVarchar",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
        "length": 256
    },
    {
        "name": "Sex",
        "type": "esriFieldTypeString",
        "alias": "Sex",
        "sqlType": "sqlTypeNVarchar",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
        "length": 256
    },
    {
        "name": "Status",
        "type": "esriFieldTypeString",
        "alias": "Status",
        "sqlType": "sqlTypeNVarchar",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
        "length": 256
    },
    {
        "name": "Provider",
        "type": "esriFieldTypeString",
        "alias": "Provider",
        "sqlType": "sqlTypeNVarchar",
        "nullable": True,
        "editable": True,
        "domain": None,
        "defaultValue": None,
        "length": 256
    }
]
