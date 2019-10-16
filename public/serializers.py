
from rest_framework import serializers


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    reason = serializers.CharField(required=False)
    message = serializers.CharField(required=True)
