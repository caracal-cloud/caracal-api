
import json
from rest_framework import serializers

from caracal.common import connections, constants
from drives.models import DriveFileAccount
from outputs.models import DataConnection


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

        user = validated_data.pop('user')
        validated_data.pop('output_agol', None)
        validated_data.pop('output_database', None)
        validated_data.pop('output_kml', None)

        validated_data['header_row_index'] -= 1
        validated_data['x_column_index'] -= 1
        validated_data['y_column_index'] -= 1
        date_column = validated_data.get('date_column_index')
        validated_data['date_column_index'] = date_column - 1 if date_column is not None else None

        gzd_column = validated_data.get('grid_zone_column_index')
        validated_data['grid_zone_column_index'] = gzd_column - 1 if gzd_column else None

        drive = DriveFileAccount.objects.create(organization=user.organization, account=user,
                                                google_oauth_access_token=user.temp_google_oauth_access_token,
                                                google_oauth_access_token_expiry=user.temp_google_oauth_access_token_expiry,
                                                google_oauth_refresh_token=user.temp_google_oauth_refresh_token,
                                                **validated_data)

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

    outputs = serializers.SerializerMethodField()
    def get_outputs(self, drive_account):
        connection = drive_account.connections.filter(agol_account__isnull=False).first()
        return {
            'output_agol': connection is not None,
            'output_database': True,
            'output_kml': drive_account.cloudwatch_update_kml_rule_names not in [None, '']
        }

    class Meta:
        model = DriveFileAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'provider', 'file_type',
                  'x_column_index', 'y_column_index', 'header_row_index',
                  'grid_zone_column_index', 'date_column_index',
                  'outputs']


class GetGoogleDocumentSheetsQueryParamsSerializer(serializers.Serializer):
    file_id = serializers.CharField(required=True)


class GetGoogleDriveFilesSerializer(serializers.Serializer):
    file_type = serializers.ChoiceField(choices=constants.DRIVE_PROVIDER_FILETYPES['google'], default='google_sheet')


class GetGoogleOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('login', 'login'), ('drive', 'drive')])
    callback = serializers.CharField(required=False)


class ReceiveGoogleOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField()


class UpdateDriveFileAccountSerializer(serializers.ModelSerializer):

    account_uid = serializers.UUIDField(required=True)

    output_agol = serializers.NullBooleanField(required=False)
    output_database = serializers.NullBooleanField(required=False)
    output_kml = serializers.NullBooleanField(required=False)

    class Meta:
        model = DriveFileAccount
        fields = ['account_uid', 'title',
                  'header_row_index', 'sheet_ids',
                  'x_column_index', 'y_column_index',
                  'grid_zone_column_index', 'date_column_index',
                  'output_agol', 'output_database', 'output_kml']

    def validate_sheet_ids(self, value):
        try:
            js_value = json.loads(value)
            if not isinstance(js_value, list):
                raise serializers.ValidationError('invalid sheet_ids, must be JSON formatted list')
        except json.JSONDecodeError:
            raise serializers.ValidationError('invalid sheet_ids, must be JSON formatted')

        return value

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs




