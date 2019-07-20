
import datetime
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import jwt
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import requests
import sentry_sdk
import traceback
import uuid

from account import serializers
from account.models import Account, Organization
from auth import cognito, tokens


class GoogleAuthView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.SocialAuthGoogleSerializer

    def post(self, request, version=None):

        serializer = serializers.SocialAuthGoogleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.data['id_token'] # do not call this id_token

        try:
            id_info = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

        except ValueError:
            traceback.print_exc()
            return Response({
                'error': 'invalid_token'
            }, status=status.HTTP_400_BAD_REQUEST)

        email = id_info['email']
        name = id_info['name']
        #locale = id_info['locale'] # maybe use locale instead of language?
        uid_google = id_info['sub'].replace('-', '')

        # get the user or create one
        try:
            # same user even if email different
            user = Account.objects.get(uid_google=uid_google)
            print('Google match found')
        except Account.DoesNotExist:
            try:
                # user already registered from email/password (different sub, same email)
                user = Account.objects.get(email=email) # user can use Google to sign into Fb acct if same email
                if user.uid_google is None:
                    user.uid_google = uid_google
                    user.save()
                print('Email match found, not Google')
            except Account.DoesNotExist:
                print('Creating new user: ', name, email)
                # create user
                # set temp short_name
                organization = Organization.objects.create(short_name=str(uuid.uuid4()), update_required=True)

                # create user in Cognito - set temp password
                pwd = str(uuid.uuid4()).split('-')[0]
                cognito_client = cognito.get_warrant_wrapper_client()
                user = Account.objects.create_user(email, pwd, cognito_client.client,
                                                   organization=organization, name=name, is_admin=True,
                                                   uid_google=uid_google, registration_method='google')

                # force the user to update their organization's name and short_name

        # invalidate previous cognito token
        #cognito.sign_out_user(email)

        access_token, access_jwt_id  = tokens.generate_access_token(str(user.uid_cognito))
        refresh_token, refresh_jwt_id = tokens.generate_refresh_token(str(user.uid_cognito))

        user.custom_access_jwt_id = access_jwt_id
        user.custom_refresh_jwt_id = refresh_jwt_id
        user.save()

        update_required = user.organization.update_required if user.organization.update_required is not None else False

        return Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'organization_update_required': update_required
        }, status=status.HTTP_200_OK)



from django.shortcuts import render
from django.views.generic.base import View


# must use localhost:8000
class TestSocialAuthView(View):
    def get(self, request, *args, **kwargs):
        context = {
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        }
        return render(request, "test_social_auth.html", context=context)


