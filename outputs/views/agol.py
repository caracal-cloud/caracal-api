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
import simple_arcgis_wrapper as saw
from urllib.parse import urlencode

from account.models import Account
from auth.backends import CognitoAuthentication
from caracal.common import agol
from caracal.common.aws_utils import cloudwatch
from outputs import serializers
from outputs.models import AgolAccount


AGOL_BASE_URL = "https://www.arcgis.com/sharing/rest/oauth2"


class DisconnectAgolView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        user = request.user

        try:
            agol_account = user.agol_account
        except AgolAccount.DoesNotExist:
            pass
        else:
            connections = agol_account.connections.all()
            for connection in connections:
                cloudwatch.delete_cloudwatch_rule(connection.cloudwatch_update_rule_name)

            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            title = f'Caracal (Disconnected - {str(now).split(".")[0]})'

            arcgis = saw.ArcgisAPI(
                access_token=agol_account.oauth_access_token,   
                refresh_token=agol_account.oauth_refresh_token, 
                username=agol_account.username,           
                client_id=settings.AGOL_CLIENT_ID
            )

            try:
                arcgis.services.update_feature_service(agol_account.feature_service_id, title=title)
            except saw.exceptions.ArcGISException as e:
                print(str(e)) # likely agol account exists in db but no service in agol

            connections.delete()
            agol_account.delete()

        user.agol_account = None
        user.save()

        return Response(status=status.HTTP_200_OK)


class GetAgolAccountView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            agol_account = user.agol_account
            
            arcgis = saw.ArcgisAPI(
                access_token=agol_account.oauth_access_token,   
                refresh_token=agol_account.oauth_refresh_token, 
                username=agol_account.username,           
                client_id=settings.AGOL_CLIENT_ID
            )

            # quick hack to see if tokens valid and can refresh
            is_connected = arcgis.requester._refresh_access_token()

            data = {
                'is_connected': is_connected,
                'username': arcgis.username
            }

        except AgolAccount.DoesNotExist:
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

        try:
            agol_account = user.agol_account
            return Response({
                'error': 'account_already_exists',
                'message': 'Account already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except AgolAccount.DoesNotExist:
            pass

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

            agol_redirect_uri = settings.HOSTNAME + reverse('agol-oauth-response')

            # exchange code for tokens
            token_url = f'{AGOL_BASE_URL}/token'
            data = {
                'client_id': settings.AGOL_CLIENT_ID,
                'code': code,
                'redirect_uri': agol_redirect_uri,
                'grant_type': 'authorization_code'
            }

            res = requests.post(token_url, data=data)
            tokens = res.json()

            # access token occasionaly missing?
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

            # check if user already has an agol account (possible if they click AGOL multiple times quickly)
            try:
                agol_account = user.agol_account
                agol_account.delete()
            except AgolAccount.DoesNotExist:
                pass

            agol_account = AgolAccount.objects.create(organization=user.organization, account=user,
                                                      oauth_access_token=access_token,
                                                      oauth_access_token_expiry=expiry,
                                                      oauth_refresh_token=refresh_token,
                                                      username=username)

            arcgis = saw.ArcgisAPI(
                access_token=access_token,   
                refresh_token=refresh_token, 
                username=username,           
                client_id=settings.AGOL_CLIENT_ID
            )
            
            service = arcgis.services.get_feature_service(name='Caracal', owner_username=username)
            if service is None:
                service = arcgis.services.create_feature_service('Caracal', 'Caracal data integration outputs')                

            if service is not None:
                agol_account.feature_service_url = service.url
                agol_account.feature_service_id = service.id
                agol_account.save()
                
                # changed a name like Caracal (Disconnected) back to Caracal
                if service.title != 'Caracal':
                    arcgis.services.update_feature_service(agol_account.feature_service_id, title='Caracal')
            else:
                sentry_sdk.capture_message(f'failed to add AGOL account to {username}')
                agol_account.delete()

            return redirect(state['callback'])


