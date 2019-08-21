from datetime import timedelta
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
import json
import os
import requests
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
from urllib.parse import urlencode

from account.models import Account
from auth.backends import CognitoAuthentication
from caracal.common import agol
from outputs import serializers

AGOL_BASE_URL = "https://www.arcgis.com/sharing/rest/oauth2"


class GetAgolAccountView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        organization = user.organization

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
        user = request.user

        state = {
            'account_uid': str(user.uid_cognito)
        }

        redirect_uri = settings.HOSTNAME + reverse('agol-oauth-response')

        params = {
            'client_id': settings.AGOL_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
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

        error = serializer.data.get('error')
        if error is not None:
            return Response({
                'error': 'access_denied'
            }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            code = serializer.data['code']
            state = serializer.data['state']
            state = json.loads(state)
            account_uid = state['account_uid'] #refresh_token user account uid

            redirect_uri = settings.HOSTNAME + reverse('agol-oauth-response')

            # exchange code for tokens
            token_url = f'{AGOL_BASE_URL}/token'
            data = {
                'client_id': settings.AGOL_CLIENT_ID,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }

            res = requests.post(token_url, data=data)
            tokens = res.json()

            access_token = tokens['access_token']
            refresh_token = tokens['refresh_token']
            username = tokens['username']

            try:
                user = Account.objects.get(uid_cognito=account_uid)
            except Account.DoesNotExist:
                return Response({
                    'error': 'account_not_found'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                user.organization.agol_username = username
                user.organization.agol_oauth_access_token = access_token
                if refresh_token:
                    user.organization.agol_oauth_refresh_token = refresh_token
                user.organization.save()

            #return Response(status=status.HTTP_200_OK)
            return redirect('https://caracal.cloud') # TODO: modify this


