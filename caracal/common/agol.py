
from django.conf import settings
import json
import requests

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
        print('match')
        return feature_service['url']


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

    print(res_data)

    if res_data.get('success', False):
        return res_data['layers'][0]['id']


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


realtime_point_fields = [
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
        "name": "DeviceId",
        "type": "esriFieldTypeString",
        "alias": "DeviceId",
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
