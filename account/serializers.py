
from django.conf import settings
from django.utils import timezone
from io import BytesIO
import pytz
from rest_framework import serializers, status
from rest_framework.response import Response
import sentry_sdk
import traceback
import uuid

from account.models import Account, Organization
from auth import cognito
from caracal.common import aws, constants, image
from caracal.common.fields import CaseInsensitiveEmailField
from botocore.exceptions import ParamValidationError


class ConfirmForgotPasswordSerializer(serializers.Serializer):

    email = CaseInsensitiveEmailField(required=True, max_length=200)
    verification_code = serializers.CharField(max_length=100)
    new_password = serializers.CharField(min_length=7, max_length=50)


class ForcedPasswordResetSerializer(serializers.Serializer):

    email = CaseInsensitiveEmailField(required=True, max_length=200)
    old_password = serializers.CharField(max_length=100)
    new_password = serializers.CharField(min_length=7, max_length=50)


class ForgotPasswordSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(required=True, max_length=200)


class GetProfileSerializer(serializers.ModelSerializer):

    organization_name = serializers.CharField(source='organization.name')
    organization_short_name = serializers.CharField(source='organization.short_name')
    organization_timezone = serializers.CharField(source='organization.timezone')

    logo_url = serializers.SerializerMethodField()
    def get_logo_url(self, obj):
        if obj.organization.logo_object_key:
            url = aws.get_presigned_url(obj.organization.logo_object_key, settings.S3_USER_DATA_TABLE, 7200)
            return url

    class Meta:
        model = Account
        fields = ['uid', 'email', 'name', 'phone_number',
                  'organization_name', 'organization_short_name',
                  'organization_timezone', 'logo_url']


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

    # TODO: add to prototype? short_name? required phone number...

    organization_name = serializers.CharField(max_length=100, required=True, allow_blank=False)
    organization_short_name = serializers.CharField(max_length=50, required=True, allow_blank=False)
    account_name = serializers.CharField(max_length=100, required=True, allow_blank=False)
    account_email = CaseInsensitiveEmailField(min_length=5, max_length=200, required=True, allow_blank=False)
    account_password = serializers.CharField(min_length=7, max_length=50, required=True, allow_blank=False)
    account_phone_number = serializers.CharField(max_length=25, required=True, allow_blank=False)

    def validate_organization_short_name(self, value):

        short_name = value.strip()
        if len(short_name.split(' ')) > 1:
            raise serializers.ValidationError({
                'error': 'invalid_organization_short_name',
                'message': 'organization short name must be one word'
            })
        return value


    def create(self, validated_data):
        organization_name = validated_data['organization_name']
        organization_short_name = validated_data['organization_short_name'].split(' ')[0].lower() # must be one word, alphanumeric
        account_name = validated_data['account_name']
        account_email = validated_data['account_email']
        account_password = validated_data['account_password']
        account_phone_number = validated_data.get('account_phone_number')

        try:
            Organization.objects.get(short_name=organization_short_name)
            raise serializers.ValidationError({
                'error': 'organization_short_name already exists',
                'message': 'organization short name already exists'
            })
        except Organization.DoesNotExist:
            pass

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
                'error': 'email_already_exists',
                'message': 'email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        except ParamValidationError:
            organization.delete()
            return Response({
                'error': 'invalid_parameter',
                'message': 'invalid parameter, min password length 7'
            })

        except:
            organization.delete()
            sentry_sdk.capture_exception()
            traceback.print_exc()


class UpdateAccountSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=150, required=False)
    phone_number = serializers.CharField(max_length=150, required=False)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.datetime_updated = timezone.now()
        instance.save()
        return instance

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


class UpdateOrganizationSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=150, required=False)
    timezone = serializers.CharField(max_length=50, required=False)
    logo = serializers.ImageField(required=False, allow_empty_file=False)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.timezone = validated_data.get('timezone', instance.timezone)
        instance.datetime_updated = timezone.now()

        organization = validated_data['organization']

        logo = validated_data.get('logo')
        if logo is not None:
            logo.file.seek(0)
            png_logo = image.get_rgba_image(logo.file.read())
            png_logo_buffer = image.get_image_bufer(png_logo)

            # standardizing ending so Lambda can use suffix filter
            object_key = f'{organization.short_name}/static/logo.{constants.DEFAULT_IMAGE_FORMAT}'
            aws.put_s3_item(png_logo_buffer.getvalue(), settings.S3_USER_DATA_TABLE, object_key)
            instance.logo_object_key = object_key

        instance.save()
        return instance

    def validate_timezone(self, timezone_string):
        if timezone_string not in pytz.all_timezones:
            raise serializers.ValidationError('invalid timezone')
        return timezone_string

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs















