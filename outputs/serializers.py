

from rest_framework import serializers


class GetAgolOauthRequestUrlQueryParamsSerializer(serializers.Serializer):
    callback = serializers.CharField(required=False)

    def validate(self, attrs):

        unknown =  set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError("Unknown field(s): {}".format(", ".join(unknown)))

        return attrs


class ReceiveAgolOauthResponseUrlQueryParamsSerializer(serializers.Serializer):

    error = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    state = serializers.CharField(required=False) # not present if access denied


