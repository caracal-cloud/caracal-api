
from datetime import datetime, timezone
from django.conf import settings
import json
import requests
from rest_framework import status
from rest_framework.response import Response
import simple_arcgis_wrapper as saw

from caracal.common import google
from outputs.models import AgolAccount


AGOL_ROOT = 'https://www.arcgis.com/sharing/rest'
X_MIN, Y_MIN, X_MAX, Y_MAX = -26, -35, 56, 39
WKID = 4326

CARACAL_SERVICE_NAME = 'Caracal'
CARACAL_SERVICE_DESCRIPTION = 'Caracal data integration outputs'

# new stuff with saw

def create_custom_source_feature_layer(title, description, feature_service, agol_account):
    
    fields = saw.fields.Fields()
    fields.add_field('Date', saw.fields.DateField)    
    fields.add_field('DeviceId', saw.fields.StringField)    
    fields.add_field('AltM', saw.fields.DoubleField)    
    fields.add_field('SpeedKmh', saw.fields.DoubleField)    
    fields.add_field('TempC', saw.fields.DoubleField)    

    feature_layer = _create_feature_layer(title, fields, feature_service, agol_account, description=description)    
    return feature_layer


def create_realtime_feature_layer(title, feature_service, agol_account):

    fields = saw.fields.Fields()
    fields.add_field('Date', saw.fields.DateField)    
    fields.add_field('DeviceId', saw.fields.StringField)    
    fields.add_field('Type', saw.fields.StringField)    
    fields.add_field('Name', saw.fields.StringField)    
    fields.add_field('Sex', saw.fields.StringField)    
    fields.add_field('Status', saw.fields.StringField)    
    fields.add_field('Provider', saw.fields.StringField)    

    feature_layer = _create_feature_layer(title, fields, feature_service, agol_account)    
    return feature_layer


def _create_feature_layer(title, fields, feature_service, agol_account, description=''):

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,   
        refresh_token=agol_account.oauth_refresh_token, 
        username=agol_account.username,           
        client_id=settings.AGOL_CLIENT_ID
    )

    feature_layer = arcgis.services.create_feature_layer(
        layer_type='point',
        name=title,
        description=description,
        feature_service_url=feature_service.url,
        fields=fields,
        x_min=X_MIN, y_min=Y_MIN,
        x_max=X_MAX, y_max=Y_MAX
    )

    return feature_layer


def delete_feature_layers(layer_ids, feature_service_url, agol_account):

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,   
        refresh_token=agol_account.oauth_refresh_token, 
        username=agol_account.username,           
        client_id=settings.AGOL_CLIENT_ID
    )

    arcgis.services.delete_feature_layers(layer_ids, feature_service_url)


def get_or_create_caracal_feature_service(agol_account):

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,   
        refresh_token=agol_account.oauth_refresh_token, 
        username=agol_account.username,           
        client_id=settings.AGOL_CLIENT_ID
    )

    feature_service = arcgis.services.get_feature_service(name=CARACAL_SERVICE_NAME, owner_username=agol_account.username)
    if feature_service is None:
        print('creating feature service')
        feature_service = arcgis.services.create_feature_service(CARACAL_SERVICE_NAME, CARACAL_SERVICE_DESCRIPTION)                

    return feature_service

def is_account_connected(agol_account):
    'Uses a hack to see if account is connected by trying to refresh token.'

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,   
        refresh_token=agol_account.oauth_refresh_token, 
        username=agol_account.username,           
        client_id=settings.AGOL_CLIENT_ID
    )

    return arcgis.requester._refresh_access_token()


# old stuff - to be removed


def create_drive_layers(drive_account, feature_service_url, agol_access_token):

    create_layer_url = feature_service_url.replace('/services/', '/admin/services/') + '/addToDefinition'

    sheet_id_to_layer_id = dict()

    if drive_account.provider == 'google':

        if drive_account.file_type == 'google_sheet':

            sheet_ids = json.loads(drive_account.sheet_ids)
            for sheet_id in sheet_ids:
                sheet_id = str(sheet_id)

                sheet_name = google.get_sheet_name(sheet_id, drive_account.file_id, google_access_token)
                if sheet_name is None:
                    print(f'invalid sheet_id: {sheet_id}')
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


def create_caracal_folder(username, access_token):

    create_folder_url = f'{AGOL_ROOT}/content/users/{username}/createFolder'

    data = {
        'title': 'Caracal',
        'f': 'json',
        'token': access_token
    }

    res = requests.post(create_folder_url, data).json()
    print(res)


def create_caracal_group(access_token):

    create_group_url = f'{AGOL_ROOT}/community/createGroup'

    data = {
        'title': 'Caracal',
        'description': 'Caracal resources',
        'access': 'private',
        'tags': 'caracal',
        'sortField': 'title',
        'sortOrder': 'asc',
        'f': 'json',
        'token': access_token
    }

    res = requests.post(create_group_url, data).json()
    if res.get('success', False):
        return res['group']['id']


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


def update_caracal_feature_service_name(new_name, agol_account):

    # first update the title, then the name
    update_service_title_url = f'{AGOL_ROOT}/content/users/{agol_account.username}/items/{agol_account.feature_service_id}/update'

    data = {
        'title': new_name,
        'f': 'json',
        'token': agol_account.oauth_access_token
    }

    title_res = requests.post(update_service_title_url, data).json()
    print(title_res)

    # https://services9.arcgis.com/gNxCsTcw53J7CAhV/arcgis/rest/admin/services/Caracal/FeatureServer/updateDefinition

    # fixme: updating the name has no effect
    """
    update_layer_url = f'{agol_account.feature_service_url.replace("services/", "admin/services/")}/updateDefinition'
    print('update_layer_url', update_layer_url)

    name_data = {
        'updateDefinition': json.dumps({
            'name': 'Caracal2'
        }),
        'f': 'json',
        'token': agol_account.oauth_access_token
    }

    name_res = requests.post(update_layer_url, name_data).json()
    print(name_res)
    """


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


def update_realtime_attribute(device_id, attributes, connection):

    access_token = connection.agol_account.oauth_access_token
    feature_service_url = connection.agol_account.feature_service_url
    layer_id = connection.agol_layer_id

    # TODO: get all the OBJECTIDs for device_id

    query_url = f'{feature_service_url}/{layer_id}/query'

    params = {
        'where': f'DeviceId = \'{device_id}\'',
        'outFields': 'OBJECTID',
        'token': access_token,
        'f': 'json'
    }

    features_res = requests.get(query_url, params).json()
    if features_res.get('error') and features_res['error'].get('code') == 498:
        connection.agol_account.oauth_access_token = refresh_access_token(connection.agol_account.oauth_refresh_token)
        connection.agol_account.save()
        params['token'] = connection.agol_account.oauth_access_token
        features_res = requests.get(query_url, params).json()

    features = features_res['features']
    print(f'updating {len(features)} features')

    feature_updates = [
        {
            'attributes': {
                'OBJECTID': f['attributes']['OBJECTID'],
                'DeviceId': device_id,
                **attributes
            }
        }
        for f in features
    ]

    update_features_url = f'{feature_service_url}/{layer_id}/updateFeatures'

    data = {
        'features': json.dumps(feature_updates),
        'token': access_token,
        'f': 'json'
    }

    res = requests.post(update_features_url, data=data).json()

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
