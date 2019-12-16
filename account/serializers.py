
from botocore.exceptions import ParamValidationError
from datetime import datetime
from datetime import timezone as tz
from django.conf import settings
from django.db import IntegrityError
from io import BytesIO
import pytz
from rest_framework import serializers, status
from rest_framework.response import Response
import sentry_sdk
import traceback
import uuid

from account.models import Account, AlertRecipient, Organization
from auth import cognito
from caracal.common import aws, constants, image, names
from caracal.common.fields import CaseInsensitiveEmailField


class AddRecipientSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlertRecipient
        fields = ['email', 'phone_number']

    def validate(self, attrs):

        organization = self.context['request'].user.organization

        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError("email or phone_number required")

        if attrs.get('email') and attrs.get('phone_number'):
            raise serializers.ValidationError("either email or phone_number, not both")

        # check if contact details exist for an active recipient at an organization
        if attrs.get('email'):
            try:
                AlertRecipient.objects.get(email=attrs['email'], organization=organization, is_active=True)
                raise serializers.ValidationError("email already exists")
            except AlertRecipient.DoesNotExist:
                pass

        if attrs.get('phone_number'):
            try:
                AlertRecipient.objects.get(phone_number=attrs['phone_number'], organization=organization, is_active=True)
                raise serializers.ValidationError("phone_number already exists")
            except AlertRecipient.DoesNotExist:
                pass

        return attrs


class ConfirmForgotPasswordSerializer(serializers.Serializer):

    email = CaseInsensitiveEmailField(required=True, max_length=200)
    verification_code = serializers.CharField(max_length=100)
    new_password = serializers.CharField(min_length=7, max_length=50)


class DeleteRecipientSerializer(serializers.Serializer):
    recipient_uid = serializers.UUIDField()


class ForceOrganizationUpdateSerializer(serializers.Serializer):

    organization_name = serializers.CharField(max_length=100, required=True, allow_blank=False)
    organization_short_name = serializers.CharField(max_length=50, required=True, allow_blank=False)

    def validate_organization_short_name(self, value):
        short_name = value.strip()
        if len(short_name.split(' ')) > 1:
            raise serializers.ValidationError({
                'error': 'invalid_organization_short_name',
                'message': 'organization short name must be one word'
            })
        return value

    def update(self, account, validated_data):

        name = validated_data['organization_name']
        short_name = validated_data['organization_short_name']

        try:
            Organization.objects.get(short_name=short_name)
            raise serializers.ValidationError({
                'error': 'organization_short_name_already_exists',
                'message': 'organization short name already exists'
            })
        except Organization.DoesNotExist:
            pass

        account.organization.name = name
        account.organization.short_name = short_name
        account.organization.update_required = False
        account.organization.save()

        password = str(uuid.uuid4()).split('-')[0]
        aws.create_dynamo_credentials(validated_data['organization_short_name'], 'admin', password, ['all'])

        return account


class ForcedPasswordResetSerializer(serializers.Serializer):

    email = CaseInsensitiveEmailField(required=True, max_length=200)
    old_password = serializers.CharField(max_length=100)
    new_password = serializers.CharField(min_length=7, max_length=50)


class ForgotPasswordSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, max_length=200)


class GetProfileSerializer(serializers.ModelSerializer):

    organization_name = serializers.CharField(source='organization.name')
    organization_short_name = serializers.CharField(source='organization.short_name')
    organization_update_required = serializers.BooleanField(source='organization.update_required')
    timezone = serializers.CharField(source='organization.timezone')

    uid = serializers.CharField(source='uid_cognito')

    logo_url = serializers.SerializerMethodField()
    def get_logo_url(self, obj):
        if obj.organization.logo_object_key:
            url = aws.get_presigned_url(obj.organization.logo_object_key, settings.S3_USER_DATA_BUCKET, 7200)
            return url

    class Meta:
        model = Account
        fields = ['uid', 'email', 'name', 'phone_number',
                  'organization_name', 'organization_short_name',
                  'organization_update_required', 'timezone',
                  'logo_url']


class GetRecipientsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlertRecipient
        fields = ['uid', 'email', 'phone_number', 'datetime_created']


class LoginSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, min_length=5, max_length=200)
    password = serializers.CharField(required=True, min_length=7, max_length=200)


class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class RefreshResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()


class RegisterSerializer(serializers.Serializer):

    organization_name = serializers.CharField(max_length=100, required=True, allow_blank=False)
    account_name = serializers.CharField(max_length=100, required=True, allow_blank=False)
    account_email = CaseInsensitiveEmailField(min_length=5, max_length=200, required=True, allow_blank=False)
    account_password = serializers.CharField(min_length=7, max_length=50, required=True, allow_blank=False)

    # TODO: remove later...
    account_phone_number = serializers.CharField(max_length=25, required=False, allow_blank=False)
    organization_short_name = serializers.CharField(min_length=4, max_length=50, required=False, allow_blank=False)

    def validate(self, attrs):

        short_name = attrs.get('organization_short_name')
        if short_name is not None:
            short_name = short_name.strip()
            if len(short_name.split(' ')) > 1:
                raise serializers.ValidationError({
                    'error': 'invalid_organization_short_name',
                    'message': 'organization short name must be one word'
                })

        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


    def create(self, validated_data):

        organization_name = validated_data['organization_name']
        account_name = validated_data['account_name']
        account_email = validated_data['account_email']
        account_password = validated_data['account_password']

        account_phone_number = validated_data.get('account_phone_number')
        organization_short_name = names.generate_unique_short_name()

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
            aws.create_dynamo_credentials(organization_short_name, 'admin', password, ['all'])
            return account

        except (IntegrityError, cognito_idp_client.exceptions.UsernameExistsException):
            organization.delete()
            raise serializers.ValidationError({
                'error': 'email_already_exists',
                'message': 'email already exists'
            })

        except ParamValidationError:
            organization.delete()
            return Response({
                'error': 'invalid_parameter',
                'message': 'invalid parameter, min password length 7'
            })

        except cognito_idp_client.exceptions.InvalidPasswordException:
            organization.delete()
            return Response({
                'error': 'invalid_password',
                'message': 'invalid password, min length 7'
            })


class SocialAuthGoogleSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class UpdateAccountSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=150, required=False)
    phone_number = serializers.CharField(max_length=150, required=False)
    organization_name = serializers.CharField(max_length=150, required=False)
    organization_short_name = serializers.CharField(max_length=50, required=False)
    timezone = serializers.CharField(max_length=50, required=False)
    logo = serializers.ImageField(required=False, allow_empty_file=False)

    def update(self, account, validated_data):

        # account
        account.name = validated_data.get('name', account.name)
        account.phone_number = validated_data.get('phone_number', account.phone_number)
        account.datetime_updated = datetime.utcnow().replace(tzinfo=tz.utc)
        account.save()

        # organization
        account.organization.name = validated_data.get('organization_name', account.organization.name)
        account.organization.timezone = validated_data.get('timezone', account.organization.timezone)

        logo = validated_data.get('logo')
        if logo is not None:
            object_key = save_logo(logo, account)
            account.organization.logo_object_key = object_key

        short_name =  validated_data.get('organization_short_name')
        if short_name is not None and short_name != account.organization.short_name:
            account.organization.short_name = short_name
            # TODO: update short_name elsewhere...

        account.organization.save()

        return account

    def validate_organization_short_name(self, short_name):
        try:
            organization = Organization.objects.get(short_name=short_name)
            if organization != self.context['request'].user.organization:
                raise serializers.ValidationError('organization_short_name must be unique')
        except Organization.DoesNotExist:
            return short_name

    def validate_timezone(self, timezone_string):
        if timezone_string not in pytz.all_timezones:
            raise serializers.ValidationError('invalid timezone')
        return timezone_string

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


def save_logo(logo, account):

    logo.file.seek(0)
    png_logo = image.get_rgba_image(logo.file.read())
    png_logo_buffer = image.get_image_bufer(png_logo)
    # standardizing ending so Lambda can use suffix filter
    object_key = f'{account.organization.short_name}/static/logo.{constants.DEFAULT_IMAGE_FORMAT}'
    aws.put_s3_item(png_logo_buffer.getvalue(), settings.S3_USER_DATA_BUCKET, object_key)
    return object_key








