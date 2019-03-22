
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
import sentry_sdk

from account.models import Account, Organization
from auth import cognito
from caracal.common.fields import CaseInsensitiveEmailField


class LoginSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, max_length=200)
    password = serializers.CharField(required=True, max_length=200)


class RegisterSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=100, required=True, allow_blank=False)
    account_name = serializers.CharField(max_length=100, required=True)
    account_email = CaseInsensitiveEmailField(required=True, max_length=200)
    account_password = serializers.CharField(required=True)
    account_phone_number = serializers.CharField(max_length=25, required=False, allow_blank=True)

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        organization_name = validated_data['organization_name']
        account_name = validated_data['account_name']
        account_email = validated_data['account_email']
        account_password = validated_data['account_password']
        account_phone_number = validated_data.get('account_phone_number')

        organization = Organization.objects.create(name=organization_name)

        cognito_idp_client = cognito.get_cognito_idp_client()

        try:
            return Account.objects.create_user(account_email,
                                               account_password,
                                               cognito_idp_client,
                                               organization=organization,
                                               name=account_name,
                                               phone_number=account_phone_number,
                                               is_admin=True)
        except cognito_idp_client.exceptions.UsernameExistsException:
            organization.delete()
            return Response({
                'error': 'email_already_exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        except:
            organization.delete()
            sentry_sdk.capture_exception()
            return Response({
                'error': 'unknown_error'
            }, status=status.HTTP_400_BAD_REQUEST)


