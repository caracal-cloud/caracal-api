
from django.conf import settings
from django.utils.encoding import smart_text
import json
import jwt
import os
from rest_framework import exceptions, status
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from sentry_sdk import capture_message
import time

from auth import cognito
from account.models import Account


class CognitoAuthentication(BaseAuthentication):

    def authenticate(self, request):

        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            return None

        try: # custom auth

            payload = jwt.decode(jwt_value, settings.SECRET_KEY, True) # cognito auth will throw exception

            if payload.get('iss') not in ['caracal.cloud', 'https://caracal.cloud']:
                raise exceptions.AuthenticationFailed({
                    'error': 'invalid_iss'
                })

            CognitoAuthentication.verify_custom_token_valid(payload)
            CognitoAuthentication.verify_expiry(payload)

            uid = payload.get('sub', None).replace('-', '')
            if uid is None:
                raise exceptions.AuthenticationFailed({
                    'error': 'sub_claim_required'
                })

        except jwt.exceptions.ExpiredSignatureError: # custom auth
            raise exceptions.AuthenticationFailed({
                'error': 'access_token_expired'
            }, status.HTTP_403_FORBIDDEN)

        except (jwt.exceptions.DecodeError, jwt.exceptions.InvalidAlgorithmError): # aws cognito auth

            CognitoAuthentication.verify_cognito_token_valid(jwt_value)
            CognitoAuthentication.verify_cognito_kid(jwt_value)

            # verify uid or username exists (both same in Cognito)
            unverified_payload = jwt.decode(jwt_value, None, False)
            uid = unverified_payload.get('sub', unverified_payload.get('username', None)).replace('-', '')
            if uid is None:
                raise exceptions.AuthenticationFailed({
                    'error': 'sub_claim_required'
                })

            CognitoAuthentication.verify_expiry(unverified_payload)

        user = Account.objects.filter(uid_cognito=uid).first()
        if user is None:
            raise exceptions.AuthenticationFailed({
                'error': 'no_user_with_sub'
            })

        return user, jwt_value


    # this cannot be static
    def get_jwt_value(self, request):

        auth = get_authorization_header(request).split()
        auth_header_prefix = settings.JWT_AUTH_HEADER_PREFIX.lower()

        if not auth:
            raise exceptions.AuthenticationFailed({
                'error': 'no_auth_header'
            })

        if smart_text(auth[0].lower()) != auth_header_prefix:
            return None

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed({
                'error': 'invalid_auth_header_no_creds',
                'detail': auth
            })
        elif len(auth) > 2:
            raise exceptions.AuthenticationFailed({
                'error': 'invalid_auth_header_spaces',
                'detail': auth
            })

        return auth[1]

    @staticmethod
    def verify_cognito_token_valid(jwt_value):
        # verify that access_token is still valid (i.e. user hasn't logged out or been revoked)
        cognito_idp_client = cognito.get_cognito_idp_client()
        try:
            cognito_idp_client.get_user(AccessToken=jwt_value.decode('utf-8'))
        except cognito_idp_client.exceptions.NotAuthorizedException:
            raise exceptions.AuthenticationFailed({
                'error': 'access_token_revoked'
            })
        except cognito_idp_client.exceptions.UserNotFoundException:
            raise exceptions.AuthenticationFailed({
                'error': 'account_not_found'
            })
        except cognito_idp_client.exceptions.ResourceNotFoundException:
            capture_message("resource_not_found: possible user pool issue", level="error")
            raise exceptions.AuthenticationFailed({
                'error': 'resource_not_found'
            })

    @staticmethod
    def verify_custom_token_valid(payload):

        uid = payload.get('sub', None)
        try:
            user = Account.objects.get(uid_cognito=uid)
            if user.custom_access_jwt_id is None or str(user.custom_access_jwt_id) != payload.get('jti', None):
                raise exceptions.AuthenticationFailed({
                    'error': 'access_token_revoked'
                })
        except Account.DoesNotExist:
            raise exceptions.AuthenticationFailed({
                'error': 'user_not_found'
            })


    @staticmethod
    def verify_expiry(unverified_payload):
        expiry_secs = unverified_payload.get('exp')
        if expiry_secs is None:
            raise exceptions.AuthenticationFailed({
                'error': 'no_exp_in_access_token'
            })
        elif expiry_secs < int(round(time.time())):
            raise exceptions.AuthenticationFailed({
                'error': 'access_token_expired'
            })

    @staticmethod
    def verify_cognito_kid(jwt_value):
        """
        Verifies that the kid in the access_token header matches a well-known kid in Cognito
        :param jwt_value:
        :return:
        """
        try:
            jwt_kid = jwt.get_unverified_header(jwt_value).get('kid')
        except jwt.exceptions.DecodeError:
            raise exceptions.AuthenticationFailed({
                'error': 'invalid_jwt'
            })

        if jwt_kid is None:
            raise exceptions.AuthenticationFailed({
                'error': 'kid_required'
            })

        jwk_path = os.path.join(settings.BASE_DIR, 'account', 'resources', 'jwks.json')
        if not os.path.isfile(jwk_path):
            capture_message("jwks_missing: jwks.json does not exist. run get_all_jwks", level="error")
            raise exceptions.AuthenticationFailed({
                'error': 'jwks_missing'
            })

        with open(jwk_path) as f:
            keys = json.loads(f.read())['keys']
        keys = [key['kid'] for key in keys]

        if not jwt_kid in keys:
            capture_message("invalid_kid: make sure JWKs retrieved (get_all_jwks)", level="error")
            raise exceptions.AuthenticationFailed({
                'error': 'invalid_kid'
            })
