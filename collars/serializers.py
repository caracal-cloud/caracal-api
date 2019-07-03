
from rest_framework import serializers
from caracal.common import constants
# from collars.models import CollarAccount, CollarIndividual

from caracal.common.models import RealTimeAccount, RealTimeIndividual


class AddCollarAccountSerializer(serializers.Serializer):

    title = serializers.CharField(max_length=100)
    provider = serializers.ChoiceField(choices=constants.ACCOUNT_PROVIDERS, required=True) # i.e. orbcomm
    type = serializers.CharField(max_length=100) # i.e. elephant

    # Orbcomm/Skygistics
    orbcomm_timezone = serializers.CharField(max_length=20, required=False)
    orbcomm_company_id = serializers.CharField(max_length=50, required=False)

    # Savannah Tracking
    savannah_tracking_username = serializers.CharField(max_length=100, required=False)
    savannah_tracking_password = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):

        # no unknown values allowed because we do **
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))

        provider = attrs['provider']
        if provider == 'orbcomm':
            if attrs.get('orbcomm_timezone') is None or attrs.get('orbcomm_company_id') is None:
                raise serializers.ValidationError('orbcomm requires orbcomm_timezone and orbcomm_company_id')
            if attrs.get('savannah_tracking_username') is not None or attrs.get('savannah_tracking_password') is not None:
                raise serializers.ValidationError('savannah tracking details not allowed')
        elif provider == 'savannah_tracking':
            if attrs.get('savannah_tracking_username') is None or attrs.get('savannah_tracking_password') is None:
                raise serializers.ValidationError('savannah_tracking requires savannah_tracking_username and savannah_tracking_password')
            if attrs.get('orbcomm_timezone') is not None or attrs.get('orbcomm_company_id') is not None:
                raise serializers.ValidationError('orbcomm details not allowed')
        else:
            raise serializers.ValidationError('invalid provider_name (use orbcomm or savannah_tracking)')

        return attrs



class GetCollarAccountsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='collar-account-detail')

    class Meta:
        model = RealTimeAccount
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'type']


class GetCollarAccountDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = RealTimeAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'type']


class GetCollarIndividualsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='rt-individual-detail')

    # TODO: calculate distances with monthly_paths

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'subtype', 'sex',
                  'datetime_last_position']


class GetCollarIndividualDetailSerializer(serializers.ModelSerializer):

    # TODO: calculate distances with monthly_paths

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'subtype', 'sex',
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
