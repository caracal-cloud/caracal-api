
from botocore.exceptions import ParamValidationError
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from account.models import Account
from account import serializers
from caracal.common.aws_utils import exceptions
from caracal.common.aws_utils import cognito


class ForcedPasswordResetView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ForcedPasswordResetSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: 'invalid_password',
        status.HTTP_401_UNAUTHORIZED: 'invalid_credentials',
        status.HTTP_403_FORBIDDEN: 'password_reset_required'
    }, security=[], operation_id='account - forced password reset')
    def post(self, request, version=None):
        if version == 'v1':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.data['email']
            old_password = serializer.data['old_password']
            new_password = serializer.data['new_password']

            try:
                cognito.reset_password_forced(email, old_password, new_password)
            except (exceptions.NotAuthorizedException, exceptions.UserNotFoundException):
                return Response({
                    'error': 'not_authorized',
                }, status=status.HTTP_403_FORBIDDEN)
            except exceptions.PasswordResetRequiredException:
                return Response({
                    'error': 'password_reset_required',
                    'message': 'use forgot password flow'
                }, status=status.HTTP_403_FORBIDDEN)
            except exceptions.ParamValidationError:
                return Response({
                    'error': 'invalid_password',
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(status=status.HTTP_200_OK)

        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ForgotPasswordView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ForgotPasswordSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: 'password_reset_rejected, limit_exceeded, invalid_email',
    }, security=[], operation_id='account - forgot password')
    def post(self, request):
        serializer = serializers.ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email']

        try:
            cognito.reset_password_start(email)
        except exceptions.NotAuthorizedException:
            return Response({
                'error': 'password_reset_rejected',
                'message': 'cannot reset password if change required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except exceptions.InvalidParameterException:
            return Response({
                'error': 'password_reset_rejected',
                'message': 'cannot reset password for non-verified accounts.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except exceptions.LimitExceededException:
            return Response({
                'error': 'limit_exceeded',
                'message': 'limit exceeded. try again later'
            }, status=status.HTTP_400_BAD_REQUEST)
        except exceptions.UserNotFoundException:
            return Response({
                'error': 'invalid_email',
                'message': 'invalid email, social media integration not yet implemented'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)


class ForgotPasswordConfirmView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ConfirmForgotPasswordSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: 'invalid_code, expired_code, invalid_password, invalid_email',
    }, security=[], operation_id='account - forced password confirm')
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email']
        verification_code = serializer.data['verification_code']
        new_password = serializer.data['new_password']

        try:
            cognito.reset_password_confirm(email, verification_code, new_password)
        except exceptions.CodeMismatchException:
            return Response({
                'error': 'invalid_code'
            }, status=status.HTTP_400_BAD_REQUEST)
        except exceptions.ExpiredCodeException:
            return Response({
                'error': 'expired_code'
            }, status=status.HTTP_400_BAD_REQUEST)
        except exceptions.UserNotFoundException:
            return Response({
                'error': 'user_not_found',
            }, status=status.HTTP_400_BAD_REQUEST)
        except exceptions.ParamValidationError:
            return Response({
                'error': 'invalid_password'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_200_OK)






