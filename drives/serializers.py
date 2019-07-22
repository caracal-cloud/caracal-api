
import json
from rest_framework import serializers

from caracal.common import constants
from drives.models import DriveFileAccount


class AddDriveFileSerializer(serializers.Serializer):

    # drive
    provider = serializers.ChoiceField(choices=constants.DRIVE_PROVIDERS)

    # file
    file_id = serializers.CharField(max_length=250, required=True)
    file_type = serializers.ChoiceField(choices=constants.DRIVE_FILETYPES, required=True)
    title = serializers.CharField(max_length=250)
    sheet_ids = serializers.CharField(max_length=250, default='*') # * means all
    header_row_index = serializers.IntegerField(required=False, min_value=0, default=0)
    coordinate_system = serializers.ChoiceField(choices=constants.COORDINATE_SYSTEMS, default='decimal degrees')

    # Outputs
    output_agol = serializers.BooleanField(default=False)
    output_database = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)

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
        # TODO: validate sheet_ids, header_row_index
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


class DeleteDriveFileSerializer(serializers.Serializer):
    account_uid = serializers.UUIDField(required=True)


class GetDriveFileAccountsSerializer(serializers.ModelSerializer):

    class Meta:
        model = DriveFileAccount
        fields = ['uid', 'datetime_created', 'datetime_updated',
                  'status', 'title', 'outputs',
                  'provider', 'file_type']


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


class UpdateDriveFileAccountSerializer(serializers.Serializer):

    account_uid = serializers.UUIDField(required=True)
    title = serializers.CharField(max_length=100, required=False)

    output_agol = serializers.BooleanField(required=False)
    output_database = serializers.BooleanField(required=False)
    output_kml = serializers.BooleanField(required=False)

    def validate(self, attrs):
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs



