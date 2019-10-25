
from datetime import datetime, timezone
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
import google_auth_oauthlib.flow
import json
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
from sentry_sdk import capture_message

from account.models import Account
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol, aws, connections
from caracal.common import google as google_utils
from caracal.common.models import get_num_sources
from drives import serializers
from drives import connections as drives_connections
from drives.models import DriveFileAccount
from outputs.models import AgolAccount


class AddDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddDriveFileSerializer

    def post(self, request):
        serializer = serializers.AddDriveFileSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        organization = user.organization

        original_data = serializer.validated_data

        num_sources = get_num_sources(organization) # unlimited source_limit is -1
        if 0 < organization.source_limit <= num_sources:
            return Response({
                'error': 'source_limit_reached',
                'message': 'You have reached the limit of your plan. Consider upgrading for unlimited sources.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # user needs to authenticate again...
        if user.temp_google_oauth_refresh_token is None:
            return Response({
                'error': 'google_login_required',
                'message': 'Request a new oauth url and log in to Google.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # make sure user has an AGOL account set up and feature service exists
        agol_account = None
        if serializer.validated_data.get('output_agol', False):
            agol_account = agol.verify_agol_state_and_get_account(user)
            if isinstance(agol_account, Response):
                return agol_account

        drive_account = serializer.save(user=request.user)

        # remove temporary google tokens...
        user.temp_google_oauth_access_token = None
        user.temp_google_oauth_access_token_expiry = None
        user.temp_google_oauth_refresh_token = None
        user.save()

        # schedule the function that pulls data from Google Sheets and adds it to S3
        schedule_res = drives_connections.schedule_drives_get_data(drive_account, organization)
        if 'error' in schedule_res:
            return Response(schedule_res, status=status.HTTP_400_BAD_REQUEST)

        drive_account.cloudwatch_get_data_rule_name = schedule_res['rule_name']
        drive_account.save()

        # this schedules AGOL and KML and adds connections
        drives_connections.schedule_drives_outputs(original_data, drive_account, user, agol_account=agol_account)

        message = f'{drive_account.provider.capitalize()} account added by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response({
            'account_uid': drive_account.uid
        }, status=status.HTTP_201_CREATED)


class DeleteDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteDriveFileSerializer

    def post(self, request):
        serializer = serializers.DeleteDriveFileSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user

        account_uid = serializer.data['account_uid']

        try:
            drive_account = DriveFileAccount.objects.get(uid=account_uid)
        except DriveFileAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if drive_account.organization != request.user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        aws.delete_cloudwatch_rule(drive_account.cloudwatch_get_data_rule_name)

        drives_connections.delete_drives_kml(drive_account)

        # TODO: delete KML files

        try:
            drives_connections.delete_drives_agol(agol_account=user.agol_account, drive_account=drive_account)
        except AgolAccount.DoesNotExist:
            pass

        drive_account.is_active = False
        drive_account.save()

        return Response(status=status.HTTP_200_OK)


class GetDriveFileAccountsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetDriveFileAccountsSerializer

    def get_queryset(self):
        organization = self.request.user.organization
        drives = DriveFileAccount.objects.filter(organization=organization, is_active=True)
        return drives


class GetGoogleDriveFilesView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleDriveFilesSerializer(data=request.query_params)
        serializer.is_valid(True)

        file_type = serializer.data['file_type']

        user = request.user

        # user needs to authenticate again...
        if user.temp_google_oauth_refresh_token is None:
            return Response({
                'error': 'google_login_required',
                'message': 'Request a new oauth url and log in to Google.'
            }, status=status.HTTP_400_BAD_REQUEST)

        access_token_expiry = user.temp_google_oauth_access_token_expiry

        # test this expiry stuff
        if access_token_expiry and access_token_expiry <= datetime.utcnow().replace(tzinfo=timezone.utc):
            # TODO update expiry
            user.temp_google_oauth_access_token = google_utils.refresh_google_token(user.temp_google_oauth_refresh_token)
            user.save()

        # fixme: documents is None sometimes - possibly to do with the temp tokens?
        documents = google_utils.get_google_drive_files(file_type, user.temp_google_oauth_access_token)

        if documents is None:
            return Response({
                'error': 'oauth_error',
                'message': 'We experienced an error trying to retrieve your documents.'
            }, status=status.HTTP_400_BAD_REQUEST)

        data = {
            "count": len(documents),
            "next": None,
            "previous": None,
            "results": documents
        }

        return Response(data=data, status=status.HTTP_200_OK)


class GetGoogleSpreadsheetSheetsView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleDocumentSheetsQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(True)

        user = request.user

        file_id = serializer.data['file_id']

        if user.temp_google_oauth_access_token_expiry <= datetime.utcnow().replace(tzinfo=timezone.utc):
            user.temp_google_oauth_access_token = google_utils.refresh_google_token(user.temp_google_oauth_refresh_token)
            user.save()

        spreadsheet = google_utils.get_google_drive_spreadsheet(file_id, access_token=user.temp_google_oauth_access_token)
        if spreadsheet is not None:
            sheets = spreadsheet['sheets']

            data = {
                "count": len(sheets),
                "next": None,
                "previous": None,
                "results": [{ # list comprehension!
                    'id': sheet['properties']['sheetId'],
                    'title': sheet['properties']['title']
                } for sheet in sheets]
            }

            return Response(data=data, status=status.HTTP_200_OK)

        else:
            return Response({
                'error': 'invalid_file',
                'message': 'the file you have request may not be the correct type'
            }, status=status.HTTP_400_BAD_REQUEST)


class GetGoogleOauthRequestUrlView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleOauthRequestUrlQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(True)

        user = request.user

        action = serializer.data['action']
        callback = serializer.data.get('callback', 'https://caracal.cloud')

        state = {
            'account_uid': str(user.uid_cognito),
            'action': action,
            'callback': callback
        }

        if action == 'login':
            scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email',
                      'https://www.googleapis.com/auth/userinfo.profile']
        else:  # drive
            scopes = ['https://www.googleapis.com/auth/drive', 'openid',
                      'https://www.googleapis.com/auth/userinfo.email',
                      'https://www.googleapis.com/auth/userinfo.profile']

        client_config = google_utils.get_google_client_config()
        flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config=client_config, scopes=scopes)

        flow.redirect_uri = settings.HOSTNAME + reverse('google-oauth-response')

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            login_hint=user.email,
            prompt='consent',
            state=json.dumps(state)
        )

        return Response({
            'authorization_url': authorization_url,
            'state': state
        }, status=status.HTTP_200_OK)


class GoogleOauthResponseView(views.APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = serializers.ReceiveGoogleOauthResponseUrlQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        error = data.get('error')
        if error is not None:
            return Response({
                'error': error
            }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            if 'code' not in data.keys() or 'state' not in data.keys():
                capture_message(f'WARNING: code or state missing: {data.get("code")} - {data.get("state")}')
                return Response({
                    'error': 'access_denied',
                    'message': 'code or state missing'
                }, status=status.HTTP_401_UNAUTHORIZED)

            code = data['code']
            state = json.loads(data['state'])
            action = state['action']

            if action == 'login':
                scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email',
                          'https://www.googleapis.com/auth/userinfo.profile']
            else: # drive
                scopes = ['https://www.googleapis.com/auth/drive', 'openid',
                          'https://www.googleapis.com/auth/userinfo.email',
                          'https://www.googleapis.com/auth/userinfo.profile']

            client_config = google_utils.get_google_client_config()
            flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config=client_config, scopes=scopes)

            flow.redirect_uri = settings.HOSTNAME + reverse('google-oauth-response')

            flow.fetch_token(code=code)
            credentials = flow.credentials

            try:
                user = Account.objects.get(uid_cognito=state['account_uid'])
            except Account.DoesNotExist:
                return Response({
                    'error': 'user_not_found'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # save temporary tokens which will be copied to the drive account when added
                # possibly fixed with prompt=consent, but if authenticating a second time it only returns access_token
                user.temp_google_oauth_access_token = credentials.token
                user.temp_google_oauth_access_token_expiry = credentials.expiry.replace(tzinfo=timezone.utc)
                if credentials.refresh_token:
                    user.temp_google_oauth_refresh_token = credentials.refresh_token
                else:
                    capture_message(f'ERROR: refresh_token is None: {user.email}')
                user.save()

            return redirect(state['callback'])


class UpdateDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateDriveFileAccountSerializer

    def post(self, request):
        serializer = serializers.UpdateDriveFileAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization

        update_data = serializer.data
        account_uid = update_data.pop('account_uid')

        # make sure user has an AGOL account set up and feature service exists
        if update_data.get('output_agol', False):
            agol_account = agol.verify_agol_state_and_get_account(user)
            if isinstance(agol_account, Response):
                return agol_account

        try:
            drive_account = DriveFileAccount.objects.get(uid=account_uid)
        except DriveFileAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        # different organization
        if drive_account.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        update_data.pop('output_agol', None)
        update_data.pop('output_database', None)
        update_data.pop('output_kml', None)

        DriveFileAccount.objects.filter(uid=account_uid).update(**update_data)

        drives_connections.update_drives_outputs(serializer.data, drive_account, user)

        message = f'{drive_account.provider.capitalize()} account updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)







