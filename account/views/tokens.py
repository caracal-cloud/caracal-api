
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics, views
from rest_framework.authentication import get_authorization_header
from rest_framework.response import Response
import sentry_sdk

from account import serializers
from account.models import Account
from auth.backends import CognitoAuthentication
from caracal.common.aws_utils import cognito, exceptions


incorrect_response = Response({
    'error': 'invalid_credentials',
    'detail': 'invalid email/password combination'
}, status=status.HTTP_403_FORBIDDEN)


def get_tokens(email, password):

    try:
        tokens = cognito.sign_in_user(email, password)
    except exceptions.NotAuthorizedException:
        return incorrect_response
    except exceptions.UserNotConfirmedException:
        return Response({ # this won't be happening since users are auto-confirmed
            'error': 'account_not_confirmed',
            'detail': 'please verify your email before logging in'
        }, status=status.HTTP_403_FORBIDDEN)
    except exceptions.UserNotFoundException:
        return incorrect_response
    except exceptions.NewPasswordRequiredError:
        return Response({
            'error': 'password_change_required',
            'detail': 'use forced password reset flow'
        }, status=status.HTTP_403_FORBIDDEN)
    else:
        return tokens


class LoginView(generics.GenericAPIView):
    """
    post:
    Return access and refresh tokens.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.LoginSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: serializers.LoginResponseSerializer,
        status.HTTP_400_BAD_REQUEST: 'email_not_confirmed', # todo: add other 400's
        status.HTTP_401_UNAUTHORIZED: 'invalid_credentials'
    }, security=[], operation_id='account - login')
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email'].lower()
        password = serializer.data['password']

        try:
            Account.objects.get(email=email, is_active=True)
        except Account.DoesNotExist:
            return incorrect_response

        token_response = get_tokens(email, password)
        if isinstance(token_response, Response): # failed
            return token_response
        else: # successful, logout of custom auth?
            return Response(token_response, status=status.HTTP_200_OK)


class LogoutView(views.APIView):
    """
    post:
    Global logout.
    """
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_401_UNAUTHORIZED: 'not_authorized'
    }, security=[], operation_id='account - logout')
    def post(self, request):

        cognito.sign_out_user(request.user.email)
        return Response(status=status.HTTP_200_OK)


class RefreshView(generics.GenericAPIView):
    """
    post:
    Return access token.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RefreshSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: serializers.RefreshResponseSerializer,
        status.HTTP_400_BAD_REQUEST: 'invalid_access_token',
    }, security=[], operation_id='account - refresh')
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.data['refresh_token']

        try:
            access_token = cognito.refresh_access_token(refresh_token)
        except exceptions.NotAuthorizedException:
            return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({
                'access_token': access_token,
            }, status=status.HTTP_200_OK)


