
from rest_framework import serializers


class AddCollarSerializer(serializers.Serializer):
    provider_name = serializers.CharField(max_length=100, required=True)
    species = serializers.CharField(max_length=100)
    # Orbcomm
    timezone= serializers.CharField(max_length=20, required=False)
    company_id = serializers.CharField(max_length=50, required=False)
    # Savannah Tracker
    username = serializers.CharField(max_length=100, required=False)
    password = serializers.CharField(max_length=100, required=False)

