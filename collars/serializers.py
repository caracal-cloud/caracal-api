
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers

from caracal.common import constants, gis
from collars.models import CollarAccount, CollarIndividual, CollarPosition


class AddCollarSerializer(serializers.Serializer):

    provider_short_name = serializers.CharField(max_length=100, required=True)
    species = serializers.CharField(max_length=100)

    orbcomm_timezone= serializers.CharField(max_length=20, required=False)
    orbcomm_company_id = serializers.CharField(max_length=50, required=False)
    savannah_tracking_username = serializers.CharField(max_length=100, required=False)
    savannah_tracking_password = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        provider = attrs['provider_short_name']
        if provider == 'orbcomm':
            if attrs.get('orbcomm_timezone') is None or attrs.get('orbcomm_company_id') is None:
                raise serializers.ValidationError('orbcomm requires orbcomm_timezone and orbcomm_company_id')
        elif provider == 'savannah_tracking':
            if attrs.get('savannah_tracking_username') is None or attrs.get('savannah_tracking_password') is None:
                raise serializers.ValidationError('savannah_tracking requires savannah_tracking_username and savannah_tracking_password')
        else:
            raise serializers.ValidationError('invalid provider_name (use orbcomm or savannah_tracking)')

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


class GetCollarAccountsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(
        lookup_field='uid',
        view_name='collar-account-detail',
    )

    provider = serializers.CharField(source='provider.name')
    provider_short_name = serializers.CharField(source='provider.short_name')

    orbcomm_company_id = serializers.SerializerMethodField()
    def get_orbcomm_company_id(self, obj):
        return obj.orbcomm_company_id[:2] + '**' if obj.orbcomm_company_id is not None else None

    savannah_tracking_password = serializers.SerializerMethodField()
    def get_savannah_tracking_password(self, obj):
        return obj.savannah_tracking_password[:3] + '***' if obj.savannah_tracking_password is not None else None

    class Meta:
        model = CollarAccount
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'provider', 'provider_short_name', 'species', 'orbcomm_timezone',
                  'orbcomm_company_id', 'savannah_tracking_username', 'savannah_tracking_password']


class GetCollarAccountDetailSerializer(serializers.ModelSerializer):

    provider = serializers.CharField(source='provider.name')
    provider_short_name = serializers.CharField(source='provider.short_name')

    orbcomm_company_id = serializers.SerializerMethodField()
    def get_orbcomm_company_id(self, obj):
        return obj.orbcomm_company_id[:2] + '**' if obj.orbcomm_company_id is not None else None

    savannah_tracking_password = serializers.SerializerMethodField()
    def get_savannah_tracking_password(self, obj):
        return obj.savannah_tracking_password[:3] + '***' if obj.savannah_tracking_password is not None else None

    class Meta:
        model = CollarAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'provider', 'provider_short_name', 'species', 'orbcomm_timezone',
                  'orbcomm_company_id', 'savannah_tracking_username', 'savannah_tracking_password']


class GetCollarIndividualsQueryParamsSerializer(serializers.Serializer):

    collar_account_uid = serializers.UUIDField(required=True)


class GetCollarIndividualsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(
        lookup_field='uid',
        view_name='collar-individual-detail',
    )

    datetime_last_reported = serializers.SerializerMethodField()
    def get_datetime_last_reported(self, individual):
        last_reported_position = CollarPosition.objects.filter(individual=individual).order_by('-datetime_recorded')[0]
        return last_reported_position.datetime_recorded

    distance_last_24_kms = serializers.SerializerMethodField() # distance traveled in last 24 hours
    def get_distance_last_24_kms(self, individual):
        then = timezone.now() - timedelta(hours=24)
        positions  = CollarPosition.objects.filter(individual=individual, datetime_recorded__gte=then).order_by('datetime_recorded')
        points = [p.position for p in positions]
        distance = gis.get_path_distance_km(points)
        return distance

    class Meta:
        model = CollarIndividual
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'name', 'sex', 'subtype', 'status',
                  'datetime_last_reported', 'distance_last_24_kms']


class GetCollarIndividualDetailSerializer(serializers.ModelSerializer):

    datetime_last_reported = serializers.SerializerMethodField()
    def get_datetime_last_reported(self, individual):
        last_reported_position = CollarPosition.objects.filter(individual=individual).order_by('-datetime_recorded')[0]
        return last_reported_position.datetime_recorded

    distance_last_24_kms = serializers.SerializerMethodField() # distance traveled in last 24 hours
    def get_distance_last_24_kms(self, individual):
        then = timezone.now() - timedelta(hours=24)
        positions  = CollarPosition.objects.filter(individual=individual, datetime_recorded__gte=then).order_by('datetime_recorded')
        points = [p.position for p in positions]
        distance = gis.get_path_distance_km(points)
        return distance

    class Meta:
        model = CollarIndividual
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'name', 'sex', 'subtype', 'status',
                  'datetime_last_reported', 'distance_last_24_kms']


class UpdateCollarAccountSerializer(serializers.Serializer):

    collar_account_uid = serializers.UUIDField(required=True)
    orbcomm_timezone= serializers.CharField(max_length=20, required=False)
    orbcomm_company_id = serializers.CharField(max_length=50, required=False)
    savannah_tracking_username = serializers.CharField(max_length=100, required=False)
    savannah_tracking_password = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        if len(attrs) < 2:
            raise serializers.ValidationError('one or more account details required')

        try:
            collar_account = CollarAccount.objects.get(uid=attrs['collar_account_uid'])
        except CollarAccount.DoesNotExist:
            raise serializers.ValidationError('invalid account uid')

        for key, value in attrs.items():
            if not key.startswith(collar_account.provider.short_name) and key != 'collar_account_uid':
                raise serializers.ValidationError('account details do not match provider: ' + collar_account.provider.short_name)

        return attrs


class UpdateCollarIndividualSerializer(serializers.Serializer):

    collar_individual_uid = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=100, required=False)
    sex = serializers.ChoiceField(['male', 'female'], required=False)
    subtype = serializers.CharField(max_length=100, required=False)
    status = serializers.ChoiceField(constants.COLLAR_STATUSES, required=False)

    def validate(self, attrs):
        return attrs