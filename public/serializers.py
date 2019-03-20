
from rest_framework import serializers


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    area = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
