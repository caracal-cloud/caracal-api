
from django.conf import settings
from rest_framework import permissions, status, generics, views
from rest_framework.authentication import get_authorization_header
from rest_framework.response import Response
import sentry_sdk
import warrant

from auth import cognito
from auth.backends import CognitoAuthentication
from account import serializers


class LoginView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.LoginSerializer

    def post(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email'].lower()
        password = serializer.data['password']

        invalid_credentials_message = 'invalid email/password combination'

        warrant_client = cognito.get_warrant_wrapper_client(email)
        try:
            tokens = cognito.get_tokens(warrant_client, password)
            return Response(tokens, status=status.HTTP_200_OK)
        except warrant_client.client.exceptions.NotAuthorizedException:
            return Response({
                'error': 'invalid_credentials',
                'message': invalid_credentials_message
            }, status=status.HTTP_403_FORBIDDEN)
        except warrant_client.client.exceptions.UserNotConfirmedException:
            return Response({
                'error': 'email_not_confirmed',
                'message': 'email not confirmed'
            }, status=status.HTTP_403_FORBIDDEN)
        except warrant_client.client.exceptions.UserNotFoundException:
            return Response({
                'error': 'invalid_credentials',
                'message': invalid_credentials_message
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


class LogoutView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        access_token = get_authorization_header(request).split()[1].decode('utf-8')
        client = cognito.get_cognito_idp_client()
        response = client.global_sign_out(AccessToken=access_token)

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return Response(status=status.HTTP_200_OK)
        else:
            sentry_sdk.capture_message("Sign out failed", level="warning")
            return Response(status=status.HTTP_400_BAD_REQUEST)



class RefreshView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RefreshSerializer

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

