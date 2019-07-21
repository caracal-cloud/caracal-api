

from rest_framework import serializers
from caracal.common import constants

from caracal.common.models import RealTimeAccount, RealTimeIndividual


class AddRtAccountSerializer(serializers.Serializer):

    title = serializers.CharField(max_length=100)
    source = serializers.ChoiceField(choices=constants.RT_ACCOUNT_SOURCES) # i.e. collar
    provider = serializers.ChoiceField(choices=constants.COLLAR_ACCOUNT_PROVIDERS, required=True) # i.e. orbcomm
    type = serializers.CharField(max_length=100) # i.e. elephant


class DeleteAccountSerializer(serializers.Serializer):
    account_uid = serializers.UUIDField(required=True)


class GetRtAccountsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='rt-account-detail')

    class Meta:
        model = RealTimeAccount
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'type']


class GetRtAccountDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = RealTimeAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'type']


class GetRtIndividualsQueryParamsSerializer(serializers.Serializer):
    account_uid = serializers.UUIDField(required=True)


class GetRtIndividualsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='rt-individual-detail')

    # TODO: calculate distances with monthly_paths

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'subtype', 'sex',
                  'blood_type', 'call_sign', 'datetime_last_position']


class GetCollarIndividualDetailSerializer(serializers.ModelSerializer):

    # TODO: calculate distances with monthly_paths

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'subtype', 'sex',
                  'blood_type', 'call_sign', 'datetime_last_position']


class UpdateRtAccountSerializer(serializers.Serializer):

    account_uid = serializers.UUIDField(required=True)
    title = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))

        return attrs


class UpdateRtIndividualSerializer(serializers.Serializer):

    individual_uid = serializers.UUIDField(required=True)
    status = serializers.ChoiceField(constants.INDIVIDUAL_STATUSES, required=False)
    name = serializers.CharField(max_length=100, required=False)
    subtype = serializers.CharField(max_length=100, required=False)
    sex = serializers.ChoiceField(choices=constants.SEXES, required=False)
    blood_type = serializers.ChoiceField(constants.BLOOD_TYPES, required=False)
    call_sign = serializers.CharField(required=False)

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs





