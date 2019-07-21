

from rest_framework import serializers

from caracal.common import constants

class AddGoogleAccountSerializer(serializers.Serializer):

    # drive
    drive_provider = serializers.ChoiceField(choices=constants.DRIVE_PROVIDERS)

    # file
    file_id = serializers.CharField(max_length=250, required=True)
    title = serializers.CharField(max_length=250)
    sheet_ids = serializers.CharField(max_length=250, default='*') # * means all
    header_row_index = serializers.IntegerField(required=False, min_value=0, default=0)
    coordinate_system = serializers.ChoiceField(choices=constants.COORDINATE_SYSTEMS, default='decimal degrees')

    # Outputs
    output_agol = serializers.BooleanField(default=False)
    output_database = serializers.BooleanField(default=False)
    output_kml = serializers.BooleanField(default=False)


    def create(self, validated_data):

        # TODO: finish me!

        # TODO: initialize title

        user = validated_data['user']

        print(validated_data)

        return None


    def validate(self, attrs):
        # TODO: validate sheet_ids, header_row_index
        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))
        return attrs


class GetGoogleDocumentSheetsQueryParamsSerializer(serializers.Serializer):
    file_id = serializers.CharField(required=True)


class GetGoogleOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('login', 'login'), ('drive', 'drive')])


class ReceiveGoogleOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField()

