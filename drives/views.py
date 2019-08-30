
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
from auth.backends import CognitoAuthentication
from caracal.common.fields import get_updated_outputs
from caracal.common import google as google_utils
from drives import serializers
from drives.models import DriveFileAccount


class AddDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddDriveFileSerializer

    def post(self, request):
        serializer = serializers.AddDriveFileSerializer(data=request.data)
        serializer.is_valid(True)

        account = serializer.save(user=request.user)

        return Response({
            'account_uid': account.uid
        }, status=status.HTTP_201_CREATED)


class DeleteDriveFileAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteDriveFileSerializer

    def post(self, request):
        serializer = serializers.DeleteDriveFileSerializer(data=request.data)
        serializer.is_valid(True)

        account_uid = serializer.data['account_uid']

        try:
            account = DriveFileAccount.objects.get(uid=account_uid)
        except DriveFileAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if account.organization != request.user.organization and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        account.is_active = False
        account.save()

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

        # TODO: make this more efficient!
        # TODO: should try google api first, if error then refresh access_token and save to org
        if user.organization.google_oauth_access_token and user.organization.google_oauth_refresh_token:
            access_token = google_utils.refresh_google_token(user.organization.google_oauth_refresh_token)
            if access_token is not None:
                user.organization.google_oauth_access_token = access_token
                user.organization.save()
                documents = google_utils.get_google_drive_files(file_type, user.organization.google_oauth_access_token)

                data = {
                    "count": len(documents),
                    "next": None,
                    "previous": None,
                    "results": documents
                }

                return Response(data=data, status=status.HTTP_200_OK)

        return Response({
            'error': 'invalid_credentials',
            'message': 'get google drive oauth request url and obtain new credentials'
        }, status=status.HTTP_403_FORBIDDEN)


class GetGoogleSpreadsheetSheetsView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleDocumentSheetsQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(True)

        user = request.user

        file_id = serializer.data['file_id']

        if user.organization.google_oauth_access_token and user.organization.google_oauth_refresh_token:
            access_token = google_utils.refresh_google_token(user.organization.google_oauth_refresh_token)
            if access_token is not None:
                user.organization.google_oauth_access_token = access_token
                user.organization.save()

                spreadsheet = google_utils.get_google_drive_spreadsheet(file_id, access_token=access_token)
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

        return Response({
            'error': 'invalid_credentials',
            'message': 'get google drive oauth request url and obtain new credentials'
        }, status=status.HTTP_403_FORBIDDEN)


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

        state = json.loads(serializer.data['state'])
        action = state['action']

        error = serializer.data.get('error')
        if error is not None:
            return Response({
                'error': error
            }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            code = serializer.data['code']

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
        user = request.user
        serializer = serializers.UpdateDriveFileAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_data = serializer.data
        account_uid = update_data.pop('account_uid')

        try:
            account = DriveFileAccount.objects.get(uid=account_uid)
        except DriveFileAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if account.organization != user.organization and not user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        outputs = get_updated_outputs(account, update_data)

        DriveFileAccount.objects.filter(uid=account_uid).update(outputs=outputs, **update_data)

        return Response(status=status.HTTP_200_OK)








