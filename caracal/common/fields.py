
from rest_framework import serializers


class CaseInsensitiveEmailField(serializers.EmailField):
    def to_representation(self, value):
        return value.lower()

