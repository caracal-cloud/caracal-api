
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


def create_custom_source_feature_layer(title, description, feature_service, agol_account):
    
    fields = saw.fields.Fields()
    fields.add_field('Date', saw.fields.DateField)    
    fields.add_field('DeviceId', saw.fields.StringField)
    fields.add_field('Name', saw.fields.StringField)    
    fields.add_field('AltM', saw.fields.DoubleField)    
    fields.add_field('SpeedKmh', saw.fields.DoubleField)    
    fields.add_field('TempC', saw.fields.DoubleField)    

    feature_layer = _create_feature_layer(title, fields, feature_service, agol_account, description=description)    
    return feature_layer


def create_drive_feature_layer(title, description, feature_service, agol_account, extra_fields=list()):

    fields = saw.fields.Fields()
    for extra_field in extra_fields:
        fields.add_field(extra_field, saw.fields.StringField)

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

    return arcgis.services.delete_feature_layers(layer_ids, feature_service_url)

def get_custom_source_features(device_id, layer_id, feature_service_url, agol_account):
    'docs'
    
    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,   
        refresh_token=agol_account.oauth_refresh_token, 
        username=agol_account.username,           
        client_id=settings.AGOL_CLIENT_ID
    ) 

    return arcgis.services.get_features(
        where=f"DeviceId = '{device_id}'",
        layer_id=layer_id,
        feature_service_url=feature_service_url,
        out_fields=['OBJECTID']
    )


def get_collar_features(device_id, layer_id, feature_service_url, agol_account):
    'docs'

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,   
        refresh_token=agol_account.oauth_refresh_token, 
        username=agol_account.username,           
        client_id=settings.AGOL_CLIENT_ID
    ) 

    return arcgis.services.get_features(
        where=f"DeviceId = '{device_id}'",
        layer_id=layer_id,
        feature_service_url=feature_service_url,
        out_fields=['OBJECTID']
    )


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


def update_features(updates, layer_id, feature_service_url, agol_account):
    'docs'

    # TODO: validate updates?

    arcgis = saw.ArcgisAPI(
        access_token=agol_account.oauth_access_token,   
        refresh_token=agol_account.oauth_refresh_token, 
        username=agol_account.username,           
        client_id=settings.AGOL_CLIENT_ID
    )

    return arcgis.services.update_features(updates, layer_id, feature_service_url)


# old stuff - to be removed

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

    # TODO: create update feature saw

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
