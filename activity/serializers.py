
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers

from activity.models import ActivityAlert, ActivityChange


class DeleteAlertSerializer(serializers.Serializer):
    alert_uid = serializers.UUIDField()


class GetAlertsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityAlert
        fields = ['uid', 'datetime_created', 'level', 'message']


class GetChangesSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityChange
        fields = ['uid', 'datetime_created', 'message']