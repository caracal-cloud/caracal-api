
from django.conf import settings
from rest_framework import permissions, status, generics
from rest_framework.response import Response
import sentry_sdk
import warrant

from auth import cognito
from account import serializers


class LoginView(generics.GenericAPIView):

    def post(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email'].lower()
        password = serializer.data['password']

        warrant_client = cognito.get_warrant_wrapper_client(email)
        try:
            tokens = cognito.get_tokens(warrant_client, password)
            # TODO: set last login...
            return Response(tokens, status=status.HTTP_200_OK)
        except warrant_client.client.exceptions.NotAuthorizedException:
            return Response({
                'error': 'invalid_credentials'
            }, status=status.HTTP_403_FORBIDDEN)
        except warrant_client.client.exceptions.UserNotConfirmedException:
            return Response({
                'error': 'email_not_confirmed'
            }, status=status.HTTP_403_FORBIDDEN)
        except warrant_client.client.exceptions.UserNotFoundException:
            return Response({
                'error': 'invalid_credentials'
            }, status=status.HTTP_403_FORBIDDEN)
        except warrant_client.client.exceptions.PasswordResetRequiredException: # RESET_REQUIRED
            return Response({
                'error': 'password_reset_required',
                'detail': 'use forgot password flow'
            }, status=status.HTTP_403_FORBIDDEN)
        except warrant.exceptions.ForceChangePasswordException: # FORCE_CHANGE_PASSWORD
            return Response({
                'error': 'password_change_required',
                'detail': 'use forced password change flow'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            sentry_sdk.capture_exception()
            return Response({
                'error': 'unknown_error',
                'detail': "%s - %s" % (type(e), str(e))
            }, status=status.HTTP_400_BAD_REQUEST)


class RefreshView(generics.GenericAPIView):

    def post(self, request):
        serializer = serializers.RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.data['refresh_token']

        cognito_idp_client = cognito.get_cognito_idp_client()
        try:
            res = cognito_idp_client.initiate_auth(
                ClientId=settings.COGNITO_APP_ID,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token,
                }
            )
        except cognito_idp_client.exceptions.NotAuthorizedException:
            return Response({
                'error': 'not_authorized'
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'access_token': res['AuthenticationResult']['AccessToken'],
        }, status=status.HTTP_200_OK)

