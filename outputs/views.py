from datetime import timedelta
from django.utils import timezone
import json
import os
import requests
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
from urllib.parse import urlencode

from outputs import serializers
from auth.backends import CognitoAuthentication

AGOL_BASE_URL = "https://www.arcgis.com/sharing/rest/oauth2"

class GetAgolOauthRequestUrlView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        client_id = 'mco5mcKtQ7f0Mvjd' # fixme: move to envars
        # client_secret = '09c98ddb4ea84f78bb948ba3d7c45b97'

        state = {
            'account_uid': str(user.uid)
        }

        params = {
            'client_id': client_id,
            'response_type': 'code',
            #'redirect_uri': 'https://api.caracal.cloud/outputs/agol/oauth/response',
            'redirect_uri': 'http://localhost:8000/outputs/agol/oauth/response',
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

        print(serializer.data.keys())

        print(serializer.data)

        error = serializer.data.get('error')
        if error is not None:
            return Response({
                'error': 'access_denied'
            }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            code = serializer.data['code']
            state = serializer.data['state']
            state = json.loads(state)
            account_uid = state['account_uid'] # user account uid

            client_id = 'mco5mcKtQ7f0Mvjd'  # fixme: move to envars

            # exchange code for tokens
            token_url = f'{AGOL_BASE_URL}/token'
            data = {
                'client_id': client_id,
                'code': code,
                #'redirect_uri': 'https://api.caracal.cloud/outputs/agol/oauth/response',
                'redirect_uri': 'http://localhost:8000/outputs/agol/oauth/response',
                'grant_type': 'authorization_code'
            }

            res = requests.post(token_url, data=data)
            tokens = res.json()

            access_token = tokens['access_token']
            refresh_token = tokens['refresh_token']
            username = tokens['username']

            # TODO: save to account

            return Response(status=status.HTTP_200_OK)