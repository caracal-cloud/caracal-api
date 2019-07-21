
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


def get_google_drive_spreadsheet(file_id, access_token):

    url = f'https://sheets.googleapis.com/v4/spreadsheets/{file_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else None



def get_google_drive_spreadsheets(access_token):

    # TODO: look into enumeration...

    url = 'https://www.googleapis.com/drive/v3/files'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    params = {
        'fields': 'files(id,name)',
        'orderBy': 'modifiedTime desc',
        'pageSize': 100,
        'q': "mimeType = 'application/vnd.google-apps.spreadsheet'"
    }

    res = requests.get(url, headers=headers, params=params)
    return res.json().get('files', None) if res.status_code == 200 else None


