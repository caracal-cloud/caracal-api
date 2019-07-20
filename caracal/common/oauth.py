
from django.conf import settings
import requests


def refresh_google_token(refresh_token):

    url = 'https://www.googleapis.com/oauth2/v4/token'
    data = {
        'refresh_token': refresh_token,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'grant_type': 'refresh_token'
    }

    res = requests.post(url=url, data=data)

    try:
        tokens = res.json()
        return tokens['access_token']
    except:
        return None
