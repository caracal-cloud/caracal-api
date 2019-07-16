

from rest_framework import serializers


class GetAgolOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    pass


class ReceiveAgolOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField(required=False) # not present if access denied
