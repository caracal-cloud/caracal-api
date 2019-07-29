
import json
from rest_framework import serializers

from caracal.common import constants
from drives.models import DriveFileAccount


class AddDriveFileSerializer(serializers.ModelSerializer):

    output_agol = serializers.BooleanField(default=False)
    output_database = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)

    class Meta:
        model = DriveFileAccount
        fields = ['provider', 'file_type', 'file_id', 'sheet_ids',
                  'title', 'header_row_index', 'coordinate_system',
                  'x_column_index', 'y_column_index',
                  'grid_zone_column_index', 'date_column_index',
                  'output_agol', 'output_database', 'output_kml']

    def create(self, validated_data):

        outputs = {
            'output_agol': validated_data.pop('output_agol', False),
            'output_database': validated_data.pop('output_database', False),
            'output_kml': validated_data.pop('output_kml', False)
        }
        outputs = json.dumps(outputs)

        drive = DriveFileAccount.objects.create(outputs=outputs, **validated_data)
        return drive

    def validate(self, attrs):

        if attrs['coordinate_system'] == 'utm' and 'grid_zone_column_index' not in attrs.keys():
            raise serializers.ValidationError('grid_zone_column_index required if utm')

        if attrs['coordinate_system'] != 'utm' and 'grid_zone_column_index' in attrs.keys():
            raise serializers.ValidationError('grid_zone_column_index not required')

        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))

        return attrs


class DeleteDriveFileSerializer(serializers.Serializer):
    account_uid = serializers.UUIDField(required=True)


class GetDriveFileAccountsSerializer(serializers.ModelSerializer):

    output_agol = serializers.SerializerMethodField()
    def get_output_agol(self, account):
        outputs = json.loads(account.outputs)
        return outputs.get('output_agol', False)

    output_database = serializers.SerializerMethodField()
    def get_output_database(self, account):
        outputs = json.loads(account.outputs)
        return outputs.get('output_database', False)

    output_kml = serializers.SerializerMethodField()
    def get_output_kml(self, account):
        outputs = json.loads(account.outputs)
        return outputs.get('output_kml', False)

    class Meta:
        model = DriveFileAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'status', 'title',
                  'provider', 'file_type',
                  'x_column_index', 'y_column_index',
                  'grid_zone_column_index', 'date_column_index',
                  'output_agol', 'output_database', 'output_kml']


class GetGoogleDocumentSheetsQueryParamsSerializer(serializers.Serializer):
    file_id = serializers.CharField(required=True)


class GetGoogleDriveFilesSerializer(serializers.Serializer):
    file_type = serializers.ChoiceField(choices=constants.DRIVE_PROVIDER_FILETYPES['google'], default='google_sheet')


class GetGoogleOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('login', 'login'), ('drive', 'drive')])


class ReceiveGoogleOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField()


class UpdateDriveFileAccountSerializer(serializers.ModelSerializer):

    account_uid = serializers.UUIDField(required=True)

    output_agol = serializers.BooleanField(default=False)
    output_database = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)

    class Meta:
        model = DriveFileAccount
        fields = ['account_uid', 'title',
                  'header_row_index',
                  'x_column_index', 'y_column_index',
                  'grid_zone_column_index', 'date_column_index',
                  'output_agol', 'output_database', 'output_kml']

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs




