
from datetime import datetime, timedelta, timezone
from django.conf import settings
import requests


def get_extra_headers(sheet_name, drive_account, access_token):

    header_data = get_spreadsheet_sheet_headers(drive_account.header_row_index, sheet_name,
                                                       drive_account.file_id, access_token)
    headers = header_data.get('values')
    if headers is None or len(headers) == 0:
        print('invalid sheet: ' + sheet_name)
        return None

    headers = headers[0]
    other_header_indices = list(range(len(headers)))

    try:
        other_header_indices.remove(drive_account.x_column_index)
        other_header_indices.remove(drive_account.y_column_index)
    except ValueError:
        print('invalid header format', headers)
        return None

    if drive_account.date_column_index:
        other_header_indices.remove(drive_account.date_column_index)

    if drive_account.coordinate_system == 'utm' and drive_account.grid_zone_column_index:
        other_header_indices.remove(drive_account.grid_zone_column_index)

    extra_headers = [headers[i] for i in other_header_indices]
    return extra_headers


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


def get_sheet_name(sheet_id, file_id, access_token):

    url = f'https://sheets.googleapis.com/v4/spreadsheets/{file_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    res = requests.get(url, headers=headers)

    for sheet in res.json()['sheets']:
        if str(sheet['properties']['sheetId']).strip() == sheet_id:
            return sheet['properties']['title']


def get_spreadsheet_sheet_data(sheet_name, file_id, access_token):

    # get the data for a sheet within a spreadsheet
    # need to lookup sheet_name before...
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{file_id}/values/{sheet_name}' # range is entire sheet
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else None


def get_spreadsheet_sheet_headers(header_row_index, sheet_name, file_id, access_token):

    row_num = header_row_index + 1
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{file_id}/values/\'{sheet_name}\'!{row_num}:{row_num}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    res = requests.get(url, headers=headers)

    return res.json() if res.status_code == 200 else dict()


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
        token_res = res.json()
        return {
            'access_token': token_res['access_token'],
            'expiry': datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=token_res['expires_in'])
        }
    except:
        return dict()


def verify_google_access_token_valid(drive_account):

    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    if drive_account.google_oauth_access_token_expiry <= now:

        token_res = refresh_google_token(drive_account.google_oauth_refresh_token)
        drive_account.google_oauth_access_token = token_res.get('access_token')
        drive_account.google_oauth_access_token_expiry = token_res.get('expiry')
        drive_account.save()


