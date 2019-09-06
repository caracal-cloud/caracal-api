from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
import json
import os
import requests
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
from sentry_sdk import capture_message
from urllib.parse import urlencode

from account.models import Account
from auth.backends import CognitoAuthentication
from caracal.common import agol
from outputs import serializers

AGOL_BASE_URL = "https://www.arcgis.com/sharing/rest/oauth2"


class DisconnectAgolView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        organization = user.organization

        if user.is_demo:
            return Response(status=status.HTTP_200_OK)

        organization.agol_oauth_access_token = None
        organization.agol_oauth_access_token_expiry = None
        organization.agol_oauth_refresh_token = None
        organization.save()

        # TODO: remove agol sync tasks...

        return Response(status=status.HTTP_200_OK)


class GetAgolAccountView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        organization = user.organization

        if user.is_demo:
            return Response({
                'is_connected': True,
                'username': 'Caracal Demo'
            }, status=status.HTTP_200_OK)

        access_token = agol.refresh_access_token(organization.agol_oauth_refresh_token)
        organization.agol_oauth_access_token = access_token
        organization.save()

        if access_token is not None:
            data = {
                'is_connected': True,
                'username': organization.agol_username
            }
        else:
            data = {
                'is_connected': False
            }

        return Response(data=data, status=status.HTTP_200_OK)


class GetAgolOauthRequestUrlView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = serializers.GetAgolOauthRequestUrlQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(True)

        callback = serializer.data.get('callback', 'https://caracal.cloud')

        user = request.user

        state = {
            'account_uid': str(user.uid_cognito),
            'callback': callback
        }

        agol_redirect_ui = settings.HOSTNAME + reverse('agol-oauth-response')

        params = {
            'client_id': settings.AGOL_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': agol_redirect_ui,
            'state': json.dumps(state)
        }
        authorization_url = f'{AGOL_BASE_URL}/authorize?{urlencode(params)}'

        return Response({
            'authorization_url': authorization_url,
            'state': state
        }, status=status.HTTP_200_OK)


class AgolOauthResponseView(views.APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = serializers.ReceiveAgolOauthResponseUrlQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        error = data.get('error')
        if error is not None:
            return Response({
                'error': 'access_denied'
            }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            # code or state occasionally missing
            if 'code' not in data.keys() or 'state' not in data.keys():
                capture_message(f'WARNING: code or state missing: {data.get("code")} - {data.get("state")}')
                return Response({
                    'error': 'access_denied',
                    'message': 'code or state missing'
                }, status=status.HTTP_401_UNAUTHORIZED)

            code = data['code']
            state = json.loads(data['state'])
            account_uid = state['account_uid'] #refresh_token user account uid

            agol_redirect_ui = settings.HOSTNAME + reverse('agol-oauth-response')

            # exchange code for tokens
            token_url = f'{AGOL_BASE_URL}/token'
            data = {
                'client_id': settings.AGOL_CLIENT_ID,
                'code': code,
                'redirect_uri': agol_redirect_ui,
                'grant_type': 'authorization_code'
            }

            res = requests.post(token_url, data=data)
            tokens = res.json()

            # access token occasionaly missing
            if 'access_token' not in tokens:
                capture_message(f'WARNING: access_token missing - {json.dumps(tokens)}')
                return Response({
                    'error': 'access_denied',
                    'message': 'access_token missing'
                }, status=status.HTTP_401_UNAUTHORIZED)

            access_token = tokens['access_token']
            refresh_token = tokens['refresh_token']
            username = tokens['username']
            expires_in = tokens['expires_in']
            expiry = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=expires_in)

            try:
                user = Account.objects.get(uid_cognito=account_uid)
            except Account.DoesNotExist:
                return Response({
                    'error': 'account_not_found'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                if user.is_demo: # do not save user's credentials if demo
                    return redirect(state['callback'])

                user.organization.agol_username = username
                user.organization.agol_oauth_access_token = access_token
                user.organization.agol_oauth_access_token_expiry = expiry
                if refresh_token:
                    user.organization.agol_oauth_refresh_token = refresh_token
                user.organization.save()

            return redirect(state['callback'])


