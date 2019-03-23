
from rest_framework import serializers

from collars.models import CollarAccount

class AddCollarSerializer(serializers.Serializer):
    provider_short_name = serializers.CharField(max_length=100, required=True)
    species = serializers.CharField(max_length=100)
    # Orbcomm
    timezone= serializers.CharField(max_length=20, required=False)
    company_id = serializers.CharField(max_length=50, required=False)
    # Savannah Tracker
    username = serializers.CharField(max_length=100, required=False)
    password = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        provider = attrs['provider_short_name']
        if provider == 'orbcomm':
            if attrs.get('timezone') is None or attrs.get('company_id') is None:
                raise serializers.ValidationError('orbcomm requires timezone and company_id')
        elif provider == 'savannah':
            if attrs.get('username') is None or attrs.get('password') is None:
                raise serializers.ValidationError('savannah requires username and password')
        else:
            raise serializers.ValidationError('invalid provider_name (use orbcomm or savannah)')

        return attrs

