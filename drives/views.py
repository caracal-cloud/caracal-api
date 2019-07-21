
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import json
import jwt
import os
import requests
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from account.models import Account
from auth.backends import CognitoAuthentication
from caracal.common.google import refresh_google_token, get_google_drive_spreadsheets
from drives import serializers


class GetGoogleDocumentsView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # TODO: make this more efficient!
        # TODO: should try google api first, if error then refresh access_token and save to org
        if user.organization.google_oauth_access_token and user.organization.google_oauth_refresh_token:
            access_token = refresh_google_token(user.organization.google_oauth_refresh_token)
            if access_token is not None:
                user.organization.google_oauth_access_token = access_token
                user.organization.save()
                documents = get_google_drive_spreadsheets(user.organization.google_oauth_access_token)

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


class GetGoogleOauthRequestUrlView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetGoogleOauthRequestUrlQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(True)

        action = serializer.data['action']

        user = request.user
        if user.organization.google_oauth_access_token and user.organization.google_oauth_refresh_token:

            access_token = refresh_google_token(user.organization.google_oauth_refresh_token)
            if access_token is not None:
                user.organization.google_oauth_access_token = access_token
                user.organization.save()

                if action == 'drive':
                    files = get_google_drive_spreadsheets(access_token)
                    if files is not None:
                        return Response({
                            'message': 'google drive already connected'
                        }, status=status.HTTP_204_NO_CONTENT)

                else:
                    return Response({
                        'message': 'google login already connected'
                    }, status=status.HTTP_204_NO_CONTENT)

        state = {
            'account_uid': str(user.uid_cognito),
            'action': action
        }

        if action == 'login':
            scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email',
                      'https://www.googleapis.com/auth/userinfo.profile']
        else:  # drive
            scopes = ['https://www.googleapis.com/auth/drive', 'openid',
                      'https://www.googleapis.com/auth/userinfo.email',
                      'https://www.googleapis.com/auth/userinfo.profile']

        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            os.path.join('drives', 'resources', 'google_oauth_client_secret.json'),
            scopes=scopes
        )

        # TODO: move to settings
        #flow.redirect_uri = 'https://api.caracal.cloud/drives/google/oauth/response'
        flow.redirect_uri = 'http://localhost:8000/drives/google/oauth/response'

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            login_hint=request.user.email,
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

        state = serializer.data['state']
        state = json.loads(state)

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

            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                os.path.join('drives', 'resources', 'google_oauth_client_secret.json'),
                scopes=scopes)

            flow.redirect_uri = 'https://api.caracal.cloud/drives/google/oauth/response'
            flow.redirect_uri = 'http://localhost:8000/drives/google/oauth/response'

            flow.fetch_token(code=code)
            credentials = flow.credentials # todo: credentials object directly...

            try:
                user = Account.objects.get(uid_cognito=state['account_uid'])
            except Account.DoesNotExist:
                return Response({
                    'error': 'user_not_found'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                user.organization.google_oauth_access_token = credentials.token
                if credentials.refresh_token:
                    user.organization.google_oauth_refresh_token = credentials.refresh_token
                user.organization.save()

            return Response(status=status.HTTP_200_OK)


