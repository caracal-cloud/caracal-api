
import json
from rest_framework import serializers

from caracal.common import connections, constants
from caracal.common.models import RealTimeAccount, RealTimeIndividual, RealTimePosition


class AddAccountSerializer(serializers.Serializer):

    provider = serializers.ChoiceField(choices=constants.RT_ACCOUNT_PROVIDERS, required=True) # trbonet

    output_agol = serializers.BooleanField(default=False)
    output_database = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)


class AddPositionSerializer(serializers.Serializer):

    # PositionMessage
    account_uid = serializers.UUIDField()
    source = serializers.CharField() # radio
    device_id = serializers.CharField()
    longitude = serializers.DecimalField(max_digits=12, decimal_places=6)
    latitude = serializers.DecimalField(max_digits=12, decimal_places=6)
    datetime_recorded = serializers.DateTimeField()


class GetRadioAccountsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='radio-account-detail')

    outputs = serializers.SerializerMethodField()
    def get_outputs(self, account):
        outputs = connections.get_outputs(account)
        return outputs

    class Meta:
        model = RealTimeAccount
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'outputs']


class GetRadioAccountDetailSerializer(serializers.ModelSerializer):

    outputs = serializers.SerializerMethodField()
    def get_outputs(self, account):
        outputs = connections.get_outputs(account)
        return outputs

    class Meta:
        model = RealTimeAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'source', 'provider', 'outputs']


class GetRadioIndividualsSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='radio-individual-detail')

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'sex', 'subtype', 'blood_type', 'call_sign',
                  'datetime_last_position', 'phone_number']


class GetRadioIndividualDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = RealTimeIndividual
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'status', 'name', 'subtype', 'sex', 'phone_number',
                  'blood_type', 'call_sign','datetime_last_position']


class UpdateRadioIndividualSerializer(serializers.Serializer):

    individual_uid = serializers.UUIDField(required=True)
    status = serializers.ChoiceField(constants.INDIVIDUAL_STATUSES, required=False)
    name = serializers.CharField(max_length=100, required=False)
    subtype = serializers.CharField(max_length=100, required=False)
    sex = serializers.ChoiceField(choices=constants.SEXES, required=False)
    blood_type = serializers.ChoiceField(choices=constants.BLOOD_TYPES, required=False)
    call_sign = serializers.CharField(max_length=100, required=False)
    phone_number = serializers.CharField(max_length=50, required=False)

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs




