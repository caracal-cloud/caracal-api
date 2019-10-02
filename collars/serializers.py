
from datetime import datetime, timedelta, timezone
import random
from rest_framework import serializers

from caracal.common import connections, constants, gis
from caracal.common.models import RealTimeAccount, RealTimeIndividual


class AddCollarAccountSerializer(serializers.ModelSerializer):

    #title = serializers.CharField(max_length=100)
    provider = serializers.ChoiceField(choices=constants.RT_ACCOUNT_PROVIDERS, required=True) # i.e. orbcomm
    type = serializers.CharField(max_length=100) # i.e. elephant

    # Orbcomm/Skygistics
    orbcomm_timezone = serializers.CharField(max_length=20, required=False)
    orbcomm_company_id = serializers.CharField(max_length=50, required=False) # fixme: should this be integer?

    # Savannah Tracking
    savannah_tracking_username = serializers.CharField(max_length=100, required=False)
    savannah_tracking_password = serializers.CharField(max_length=100, required=False)

    # Outputs
    output_agol = serializers.BooleanField(default=False)
    output_database = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)

    class Meta:
        model = RealTimeAccount
        fields = ['provider', 'type',
                  'orbcomm_timezone', 'orbcomm_company_id',
                  'savannah_tracking_username', 'savannah_tracking_password',
                  'output_agol', 'output_database', 'output_kml']

    def validate(self, attrs):
        # no unknown values allowed because we do **
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))

        validate_provider_details(attrs)

        # TODO: verify that exclusively savannah or orbcomm

        return attrs


class GetCollarAccountsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='collar-account-detail')

    outputs = serializers.SerializerMethodField()
    def get_outputs(self, realtime_account):
        connection = realtime_account.connections.filter(agol_account__isnull=False).first()
        return {
            'output_agol': connection is not None,
            'output_database': True,
            'output_kml': realtime_account.cloudwatch_update_kml_rule_names not in [None, '']
        }

    class Meta:
        model = RealTimeAccount
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'type', 'outputs']


class GetCollarAccountDetailSerializer(serializers.ModelSerializer):

    outputs = serializers.SerializerMethodField()
    def get_outputs(self, account):
        outputs = connections.get_outputs(account)
        return outputs

    class Meta:
        model = RealTimeAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'type', 'outputs']


class GetCollarIndividualsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='collar-individual-detail')

    distance_day = serializers.SerializerMethodField()
    def get_distance_day(self, individual): # kms
        then = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=24)
        positions = individual.rt_positions.filter(datetime_recorded__gte=then).order_by('datetime_recorded')
        positions = [p.position for p in positions]
        return gis.get_path_distance_km(positions) if len(positions) > 2 else 0

    datetime_last_position = serializers.SerializerMethodField()
    def get_datetime_last_position(self, individual):
        last_position = individual.rt_positions.order_by('-datetime_recorded').first()
        return last_position.datetime_recorded

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'device_id', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'subtype', 'sex', 'distance_day',
                  'datetime_last_position']


class GetCollarIndividualDetailSerializer(serializers.ModelSerializer):

    distance_day = serializers.SerializerMethodField()
    def get_distance_day(self, individual): # kms
        then = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=24)
        positions = individual.rt_positions.filter(datetime_recorded__gte=then).order_by('datetime_recorded')
        positions = [p.position for p in positions]
        return gis.get_path_distance_km(positions) if len(positions) > 2 else 0

    datetime_last_position = serializers.SerializerMethodField()
    def get_datetime_last_position(self, individual):
        last_position = individual.rt_positions.order_by('-datetime_recorded').first()
        return last_position.datetime_recorded

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'device_id', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'subtype', 'sex', 'distance_day',
                  'datetime_last_position']


class UpdateCollarIndividualSerializer(serializers.Serializer):

    individual_uid = serializers.UUIDField(required=True)
    status = serializers.ChoiceField(constants.INDIVIDUAL_STATUSES, required=False)
    name = serializers.CharField(max_length=100, required=False)
    subtype = serializers.CharField(max_length=100, required=False)
    sex = serializers.ChoiceField(choices=constants.SEXES, required=False)

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


class ValidateAccountDetailsSerializer(serializers.Serializer):

    provider = serializers.ChoiceField(choices=constants.RT_ACCOUNT_PROVIDERS, required=True) # i.e. orbcomm

    # Orbcomm/Skygistics
    orbcomm_company_id = serializers.CharField(max_length=50, required=False)
    orbcomm_timezone = serializers.CharField(max_length=20, required=False)

    # Savannah Tracking
    savannah_tracking_username = serializers.CharField(max_length=100, required=False)
    savannah_tracking_password = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        validate_provider_details(attrs)
        return attrs


def validate_provider_details(attrs):

    provider = attrs['provider']
    if provider == 'orbcomm':
        if attrs.get('orbcomm_timezone') is None or attrs.get('orbcomm_company_id') is None:
            raise serializers.ValidationError('orbcomm requires orbcomm_timezone and orbcomm_company_id')
        if attrs.get('savannah_tracking_username') is not None or attrs.get('savannah_tracking_password') is not None:
            raise serializers.ValidationError('savannah tracking details not allowed')
    elif provider == 'savannah_tracking':
        if attrs.get('savannah_tracking_username') is None or attrs.get('savannah_tracking_password') is None:
            raise serializers.ValidationError(
                'savannah_tracking requires savannah_tracking_username and savannah_tracking_password')
        if attrs.get('orbcomm_timezone') is not None or attrs.get('orbcomm_company_id') is not None:
            raise serializers.ValidationError('orbcomm details not allowed')
    else:
        raise serializers.ValidationError('invalid provider_name (orbcomm or savannah_tracking)')












