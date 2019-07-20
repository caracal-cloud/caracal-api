
import google.oauth2.credentials
import google_auth_oauthlib.flow
import json
import os
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from account.models import Account
from auth.backends import CognitoAuthentication
from drives import serializers


class GetGoogleOauthRequestUrlView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        # TODO: check if google oauth creds already connected

        state = {
            'account_uid': request.user.uid_cognito
        }

        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            os.path.join('drives', 'resources', 'google_oauth_client_secret.json'),
            scopes=['https://www.googleapis.com/auth/drive']
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

        error = serializer.data.get('error')
        if error is not None:
            return Response({
                'error': error
            }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            code = serializer.data['code']

            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                os.path.join('drives', 'resources', 'google_oauth_client_secret.json'),
                scopes=['https://www.googleapis.com/auth/drive'],

            )

            flow.redirect_uri = 'https://api.caracal.cloud/drives/google/oauth/response'
            flow.redirect_uri = 'http://localhost:8000/drives/google/oauth/response'

            flow.fetch_token(code=code)
            credentials = flow.credentials

            access_token = credentials.token
            refresh_token = credentials.refresh_token

            print('access_token', access_token)
            print('refresh_token', refresh_token)

            # TODO: save tokens to user's organization
            try:
                user = Account.objects.get(uid_cognito=state['account_uid'])
            except Account.DoesNotExist:
                return Response({
                    'error': 'user_not_found'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                user.organization.google_oauth_access_token = access_token
                user.organization.google_oauth_refresh_token = refresh_token
                user.organization.save()

            return Response(status=status.HTTP_200_OK)


