

from rest_framework import serializers


class AddGoogleAccountSerializer(serializers.Serializer):
    file_id = serializers.CharField(required=True)
    header_row = serializers.IntegerField(required=False, default=0)

    title = serializers.CharField(required=False)


class GetGoogleDocumentSheetsQueryParamsSerializer(serializers.Serializer):
    file_id = serializers.CharField(required=True)


class GetGoogleOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('login', 'login'), ('drive', 'drive')])


class ReceiveGoogleOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField()
