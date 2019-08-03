
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


def get_google_client_config():
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "project_id": "caracal",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": ["https://api.caracal.cloud/drives/google/oauth/response",
                              "http://localhost:8000/drives/google/oauth/response"]
        }
    }


def get_google_drive_spreadsheet(file_id, access_token):

    url = f'https://sheets.googleapis.com/v4/spreadsheets/{file_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else None



def get_google_drive_files(file_type, access_token):

    # TODO: look into enumeration...

    url = 'https://www.googleapis.com/drive/v3/files'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    if file_type == 'google_sheet':
        mime_type = 'application/vnd.google-apps.spreadsheet'
    elif file_type == 'csv':
        mime_type = 'text/csv'
    else:
        mime_type = 'application/vnd.google-apps.spreadsheet'

    params = {
        'fields': 'files(id,name)',
        'orderBy': 'modifiedTime desc',
        'pageSize': 100,
        'q': f"mimeType = '{mime_type}'"
    }

    res = requests.get(url, headers=headers, params=params)
    return res.json().get('files', None) if res.status_code == 200 else None


