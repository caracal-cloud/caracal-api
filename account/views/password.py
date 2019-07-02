
from botocore.exceptions import ParamValidationError
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics
from rest_framework.response import Response
import warrant

from auth import cognito
from account import serializers


class ForcedPasswordResetView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ForcedPasswordResetSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: 'invalid_password',
        status.HTTP_401_UNAUTHORIZED: 'invalid_credentials',
        status.HTTP_403_FORBIDDEN: 'password_reset_required'
    })
    def post(self, request):
        serializer = serializers.ForcedPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email']
        old_password = serializer.data['old_password']
        new_password = serializer.data['new_password']

        warrant_client = cognito.get_warrant_wrapper_client(email)
        try:
            cognito.get_tokens(warrant_client, old_password)
            return Response({
                'detail': 'password reset not required'
            }, status=status.HTTP_200_OK)
        except warrant.exceptions.ForceChangePasswordException: # FORCE_CHANGE_PASSWORD
            try:
                warrant_client.new_password_challenge(old_password, new_password)
                return Response(status=status.HTTP_200_OK)
            except warrant_client.client.exceptions.InvalidPasswordException:
                return Response({
                    'error': 'invalid_password',
                }, status=status.HTTP_400_BAD_REQUEST)
        except (warrant_client.client.exceptions.NotAuthorizedException, warrant_client.client.exceptions.UserNotFoundException):
            return Response({
                'error': 'invalid_credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except warrant_client.client.exceptions.PasswordResetRequiredException: # RESET_REQUIRED
            return Response({
                'error': 'password_reset_required',
                'detail': 'use forgot password flow'
            }, status=status.HTTP_403_FORBIDDEN)


class ForgotPasswordView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ForgotPasswordSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: 'password_reset_rejected, limit_exceeded, invalid_email',
    })
    def post(self, request):
        serializer = serializers.ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email']

        warrant_client = cognito.get_warrant_wrapper_client(email)
        try:
            warrant_client.initiate_forgot_password()
            return Response(status=status.HTTP_200_OK)
        except warrant_client.client.exceptions.NotAuthorizedException:
            return Response({
                'error': 'password_reset_rejected',
                'message': 'cannot reset password if change required'
            }, status=status.HTTP_400_BAD_REQUEST)
        except warrant_client.client.exceptions.InvalidParameterException:
            return Response({
                'error': 'password_reset_rejected',
                'message': 'cannot reset password for non-verified accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        except warrant_client.client.exceptions.LimitExceededException:
            return Response({
                'error': 'limit_exceeded',
                'message': 'try again later'
            }, status=status.HTTP_400_BAD_REQUEST)
        except warrant_client.client.exceptions.UserNotFoundException:
            return Response({
                'error': 'invalid_email',
                'message': 'invalid email'
            }, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordConfirmView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ConfirmForgotPasswordSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: 'invalid_code, expired_code, invalid_password, invalid_email',
    })
    def post(self, request):
        serializer = serializers.ConfirmForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email']
        confirmation_code = serializer.data['confirmation_code']
        new_password = serializer.data['new_password']

        warrant_client = cognito.get_warrant_wrapper_client(email)
        try:
            warrant_client.confirm_forgot_password(confirmation_code, new_password)
            return Response(status=status.HTTP_200_OK)
        except warrant_client.client.exceptions.CodeMismatchException:
            return Response({
                'error': 'invalid_code',
                'message': 'invalid code'
            }, status=status.HTTP_400_BAD_REQUEST)
        except warrant_client.client.exceptions.ExpiredCodeException:
            return Response({
                'error': 'expired_code',
                'message': 'code expired, please try again'
            }, status=status.HTTP_400_BAD_REQUEST)
        except ParamValidationError:
            return Response({
                'error': 'invalid_password',
                'message': 'invalid password'
            }, status=status.HTTP_400_BAD_REQUEST)
        except warrant_client.client.exceptions.UserNotFoundException:
            return Response({
                'error': 'invalid_email',
                'message': 'invalid email'
            }, status=status.HTTP_400_BAD_REQUEST)