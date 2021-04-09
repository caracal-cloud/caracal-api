from rest_framework import serializers

from caracal.common import constants, models
from jackal.models import WhatsAppCall


class AddWhatsAppCallSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField(required=False)
    timestamp_recorded = serializers.IntegerField(required=False)

    user_jid_id = serializers.IntegerField()
    user_user_string = serializers.CharField()

    call_log_id = serializers.IntegerField()
    duration_secs = serializers.IntegerField()
    from_me = serializers.BooleanField(default=True)

    def validate(self, attrs):
        return validate_unknown_attrs(attrs, self.initial_data, self.fields)


class AddWhatsAppGroupParticipantSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField(required=False)
    timestamp_recorded = serializers.IntegerField(required=False)

    group_jid_id = serializers.IntegerField()
    group_subject = serializers.CharField()
    group_user_string = serializers.CharField()

    user_jid_id = serializers.IntegerField()
    user_user_string = serializers.CharField()


class AddWhatsAppMessageSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField(required=False)
    timestamp_recorded = serializers.IntegerField(required=False)

    group_jid_id = serializers.IntegerField(required=False)
    group_user_string = serializers.CharField(required=False)
    user_jid_id = serializers.IntegerField(required=False)
    user_user_string = serializers.CharField(required=False)

    from_me = serializers.BooleanField()
    media_url = serializers.CharField(required=False)
    message = serializers.CharField(required=False)
    messages_id = serializers.IntegerField()


class AddWhatsAppUserSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField(required=False)
    timestamp_recorded = serializers.IntegerField(required=False)

    user_jid_id = serializers.IntegerField()
    user_user_string = serializers.CharField()

def validate_unknown_attrs(attrs, initial_data, fields):
    unknown = set(initial_data) - set(fields)
    if unknown:
        raise serializers.ValidationError(
            "Unknown field(s): {}".format(", ".join(unknown))
        )
    return attrs