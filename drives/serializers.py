

from rest_framework import serializers


class GetGoogleOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('login', 'login'), ('drive', 'drive')])


class ReceiveGoogleOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField()
