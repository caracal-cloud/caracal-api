
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.validators import UniqueValidator
import sentry_sdk
import traceback
import uuid

from account.models import Account, Organization
from auth import cognito
from caracal.common import aws
from caracal.common.fields import CaseInsensitiveEmailField


class ConfirmForgotPasswordSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, max_length=200)
    confirmation_code = serializers.CharField(max_length=100)
    new_password = serializers.CharField(max_length=100)


class ForcedPasswordResetSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, max_length=200)
    old_password = serializers.CharField(max_length=100)
    new_password = serializers.CharField(max_length=100)


class ForgotPasswordSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, max_length=200)


class LoginSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, max_length=200)
    password = serializers.CharField(required=True, max_length=200)


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=100, required=True, allow_blank=False)
    organization_short_name = serializers.CharField(max_length=50, required=True, allow_blank=False)
    account_name = serializers.CharField(max_length=100, required=True)
    account_email = CaseInsensitiveEmailField(required=True, max_length=200)
    account_password = serializers.CharField(required=True)
    account_phone_number = serializers.CharField(max_length=25, required=False, allow_blank=True)

    def validate_organization_short_name(self, value):
        # UniqueValidator wasn't working
        try:
            Organization.objects.get(short_name=value)
            raise serializers.ValidationError('short_name_already_exists')
        except Organization.DoesNotExist:
            return value

    def create(self, validated_data):
        organization_name = validated_data['organization_name']
        organization_short_name = validated_data['organization_short_name'].split(' ')[0].lower() # must be one word, alphanumeric
        account_name = validated_data['account_name']
        account_email = validated_data['account_email']
        account_password = validated_data['account_password']
        account_phone_number = validated_data.get('account_phone_number')

        organization = Organization.objects.create(name=organization_name, short_name=organization_short_name)

        cognito_idp_client = cognito.get_cognito_idp_client()

        try:
            account = Account.objects.create_user(account_email,
                                               account_password,
                                               cognito_idp_client,
                                               organization=organization,
                                               name=account_name,
                                               phone_number=account_phone_number,
                                               is_admin=True)

            # create credentials for S3
            password = str(uuid.uuid4()).split('-')[0]
            aws.create_dynamo_credentials(validated_data['organization_short_name'], 'admin', password, ['all'])

            return account

        except cognito_idp_client.exceptions.UsernameExistsException:
            organization.delete()
            return Response({
                'error': 'email_already_exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        except:
            organization.delete()
            sentry_sdk.capture_exception()
            traceback.print_exc()
