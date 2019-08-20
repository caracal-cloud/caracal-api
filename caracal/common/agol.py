
from django.conf import settings
import requests

AGOL_ROOT = 'https://www.arcgis.com/sharing/rest'


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