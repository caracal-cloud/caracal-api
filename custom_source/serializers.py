
from rest_framework import serializers
import uuid

from custom_source.models import Source


class AddSourceSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False)

    def create(self, validated_data):

        account = validated_data.pop('account')
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


class GetSourcesSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(lookup_field='uid', view_name='source-detail')

    class Meta:
        model = Source
        fields = ['url', 'uid', 'datetime_created', 'datetime_updated',
                  'name', 'description', 'write_key']


class GetSourceDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Source
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'name', 'description', 'write_key']


class UpdateSourceSerializer(serializers.Serializer):

    source_uid = serializers.UUIDField(required=True)

    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)


class TempAddRecordSerializer(serializers.Serializer):

    write_key = serializers.CharField()

    datetime_recorded = serializers.DateTimeField()
    lat = serializers.DecimalField(max_digits=12, decimal_places=6)
    lon = serializers.DecimalField(max_digits=12, decimal_places=6)

    alt_m = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    device_id = serializers.CharField(max_length=100, required=False)
    speed_kmh = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    temp_c = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)