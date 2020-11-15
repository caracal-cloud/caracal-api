
from rest_framework import serializers
import uuid

from custom_source.models import Device, Source


class AddRecordSerializer(serializers.Serializer):

    write_key = serializers.CharField()

    datetime_recorded = serializers.DateTimeField()
    lat = serializers.DecimalField(max_digits=None, decimal_places=None)
    lon = serializers.DecimalField(max_digits=None, decimal_places=None)
    device_id = serializers.CharField(max_length=100)

    alt_m = serializers.DecimalField(max_digits=None, decimal_places=None, required=False)
    speed_kmh = serializers.DecimalField(max_digits=None, decimal_places=None, required=False)
    temp_c = serializers.DecimalField(max_digits=None, decimal_places=None, required=False)


class AddSourceSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False)

    output_agol = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)

    def create(self, validated_data):

        account = validated_data.pop('account')
        validated_data.pop('output_agol')
        validated_data.pop('output_kml')

        write_key = str(uuid.uuid4()).replace('-', '')

        source = Source.objects.create(account=account, organization=account.organization,
                                       write_key=write_key, **validated_data)
        return source

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


class DeleteSourceSerializer(serializers.Serializer):
    source_uid = serializers.UUIDField(required=True)


class GetDevicesQueryParamsSerializer(serializers.Serializer):
    source_uid = serializers.UUIDField(required=True)


class GetDevicesSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='device-detail')

    class Meta:
        model = Device
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'name', 'description', 'device_id']


class GetDeviceDetailSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Device
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'name', 'description', 'device_id']


class GetSourcesSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='source-detail')

    outputs = serializers.SerializerMethodField()
    def get_outputs(self, source):
        connection = source.connections.filter(agol_account__isnull=False).first()
        return {
            'output_agol': connection is not None,
            'output_database': True,
            'output_kml': source.cloudwatch_update_kml_rule_names not in [None, '']
        }

    class Meta:
        model = Source
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'name', 'description', 'write_key', 'outputs']


class GetSourceDetailSerializer(serializers.ModelSerializer):

    outputs = serializers.SerializerMethodField()
    def get_outputs(self, source):
        connection = source.connections.filter(agol_account__isnull=False).first()
        return {
            'output_agol': connection is not None,
            'output_database': True,
            'output_kml': source.cloudwatch_update_kml_rule_names not in [None, '']
        }

    class Meta:
        model = Source
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'name', 'description', 'write_key', 'outputs']


class UpdateDeviceSerializer(serializers.Serializer):

    device_uid = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs



class UpdateSourceSerializer(serializers.Serializer):

    source_uid = serializers.UUIDField(required=True)

    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)

    output_agol = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs

