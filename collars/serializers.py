
from rest_framework import serializers

from caracal.common import constants
from collars.models import CollarAccount


class AddCollarSerializer(serializers.Serializer):
    provider_short_name = serializers.CharField(max_length=100, required=True)
    species = serializers.CharField(max_length=100)
    # Orbcomm
    orbcomm_timezone= serializers.CharField(max_length=20, required=False)
    orbcomm_company_id = serializers.CharField(max_length=50, required=False)
    # Savannah Tracker
    savannah_username = serializers.CharField(max_length=100, required=False)
    savannah_password = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        provider = attrs['provider_short_name']
        if provider == 'orbcomm':
            if attrs.get('orbcomm_timezone') is None or attrs.get('orbcomm_company_id') is None:
                raise serializers.ValidationError('orbcomm requires orbcomm_timezone and orbcomm_company_id')
        elif provider == 'savannah':
            if attrs.get('savannah_username') is None or attrs.get('savannah_password') is None:
                raise serializers.ValidationError('savannah requires savannah_username and savannah_password')
        else:
            raise serializers.ValidationError('invalid provider_name (use orbcomm or savannah)')

        return attrs


class AddCollarIndividualSerializer(serializers.Serializer):
    collar_account_uid = serializers.UUIDField(required=True)
    collar_id = serializers.CharField(max_length=100, required=True)

    def validate(self, attrs):
        return attrs

class AddCollarIndividualPositionSerializer(serializers.Serializer):
    collar_individual_uid = serializers.UUIDField(required=True)
    datetime_recorded = serializers.DateTimeField()
    latitude = serializers.DecimalField(decimal_places=6, max_digits=12)
    longitude = serializers.DecimalField(decimal_places=6, max_digits=12)

    def validate(self, attrs):
        return attrs


class UpdateCollarIndividualSerializer(serializers.Serializer):
    collar_account_uid = serializers.UUIDField(required=True)
    collar_id = serializers.CharField(max_length=50, required=True)
    name = serializers.CharField(max_length=100, required=False)
    sex = serializers.ChoiceField(['male', 'female'], required=False)
    subtype = serializers.CharField(max_length=100, required=False)
    status = serializers.ChoiceField(constants.COLLAR_STATUSES, required=False)

    def validate(self, attrs):
        return attrs