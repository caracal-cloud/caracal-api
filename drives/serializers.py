

from rest_framework import serializers


class GetGoogleOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    account_uid = serializers.UUIDField(required=True)


class ReceiveGoogleOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField()
