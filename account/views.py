
from django.conf import settings
from rest_framework import permissions, status, generics
from rest_framework.response import Response
import sentry_sdk
import uuid

from auth import cognito
from auth.backends import CognitoAuthentication
from account import serializers
from account.models import Account, Organization


class LoginView(generics.GenericAPIView):

    def post(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.data['email'].lower()
        password = serializer.data['password']

        cognito_idp_client = cognito.get_cognito_idp_client()

        try:
            tokens = cognito.get_tokens(email, password, cognito_idp_client)
            return Response(tokens, status=status.HTTP_200_OK)
        except cognito_idp_client.exceptions.NotAuthorizedException:
            return Response({
                'error': 'invalid_credentials'
            }, status=status.HTTP_403_FORBIDDEN)
        except cognito_idp_client.exceptions.UserNotConfirmedException:
            return Response({
                'error': 'email_not_confirmed'
            }, status=status.HTTP_403_FORBIDDEN)
        except cognito_idp_client.exceptions.UserNotFoundException:
            return Response({
                'error': 'invalid_credentials'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            sentry_sdk.capture_exception()
            return Response({
                'error': 'unknown_error',
                'detail': "%s - %s" % (type(e), str(e))
            }, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(generics.GenericAPIView):

    def post(self, request):
        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = serializer.save()
        if isinstance(response, Response):
            return response
        else:
            return Response(status=status.HTTP_201_CREATED)

