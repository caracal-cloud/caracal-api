from rest_framework import serializers

from caracal.common import constants, models
from jackal.models import Call, Contact, Location, Network, OtherPhone, Phone, Text


class AddCallSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField()

    is_sent = serializers.BooleanField(required=True)
    other_phone_number = serializers.CharField(max_length=50)
    duration_secs = serializers.IntegerField()

    def validate(self, attrs):
        return validate_unknown_attrs(attrs, self.initial_data, self.fields)


class AddContactSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField()

    name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=50)

    def validate(self, attrs):
        return validate_unknown_attrs(attrs, self.initial_data, self.fields)


class AddLocationSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField()

    latitude = serializers.DecimalField(max_digits=None, decimal_places=None)
    longitude = serializers.DecimalField(max_digits=None, decimal_places=None)
    accuracy_m = serializers.DecimalField(max_digits=None, decimal_places=None)

    def validate(self, attrs):
        return validate_unknown_attrs(attrs, self.initial_data, self.fields)


class AddLogSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField()

    level = serializers.CharField(max_length=50)
    message = serializers.CharField()


class AddTextSerializer(serializers.Serializer):

    write_key = serializers.CharField(max_length=100)
    device_id = serializers.CharField(max_length=100)
    datetime_recorded = serializers.DateTimeField()

    is_sent = serializers.BooleanField()
    other_phone_number = serializers.CharField(max_length=50)
    message = serializers.CharField()

    def validate(self, attrs):
        return validate_unknown_attrs(attrs, self.initial_data, self.fields)


class CreateNetworkSerializer(serializers.Serializer):
    output_agol = serializers.NullBooleanField(required=False)
    output_kml = serializers.NullBooleanField(required=False)


class GetPhonesSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(
        lookup_field="uid", view_name="phone-detail"
    )

    # TODO: update this
    datetime_last_update = serializers.SerializerMethodField()
    def get_datetime_last_update(self, phone):
        return models.get_utc_datetime_now()

    class Meta:
        model = Phone
        fields = [
            "url",
            "uid",
            "device_id",
            "status",
            "name",
            "description",
            "mark",
            "phone_numbers",
            "datetime_last_update",
        ]


# Recording Serializers


class OtherPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherPhone
        fields = ["phone_number", "name", "description", "mark"]


class CallSerializer(serializers.ModelSerializer):

    other_phone = OtherPhoneSerializer()

    class Meta:
        model = Call
        fields = ["datetime_recorded", "other_phone", "is_sent", "duration_secs"]


class ContactSerializer(serializers.ModelSerializer):

    other_phone = OtherPhoneSerializer()

    class Meta:
        model = Contact
        fields = ["datetime_recorded", "other_phone"]


class LocationSerializer(serializers.ModelSerializer):

    longitude = serializers.SerializerMethodField()

    def get_longitude(self, location):
        return location.position.coords[0]

    latitude = serializers.SerializerMethodField()

    def get_latitude(self, location):
        return location.position.coords[1]

    accuracy_m = serializers.SerializerMethodField()

    def get_accuracy_m(self, location):
        return round(float(location.accuracy_m), 2)

    class Meta:
        model = Location
        fields = ["datetime_recorded", "longitude", "latitude", "accuracy_m"]


class TextSerializer(serializers.ModelSerializer):

    other_phone = OtherPhoneSerializer()

    class Meta:
        model = Text
        fields = ["datetime_recorded", "other_phone", "is_sent", "message"]


class GetNetworkSerializer(serializers.ModelSerializer):

    outputs = serializers.SerializerMethodField()

    # TODO: update me
    csv_url = serializers.SerializerMethodField()
    def get_csv_url(self, network):
        return "https://public.caracal.cloud/example.csv"

    def get_outputs(self, network):
        connection = network.connections.filter(agol_account__isnull=False).first()
        return {
            "output_agol": connection is not None,
            "output_database": True,
            "output_kml": False,  # FIXME: network.cloudwatch_update_kml_rule_names not in [None, '']
        }

    class Meta:
        model = Network
        fields = ["uid", "write_key", "outputs", 'csv_url']


class GetPhoneDetailSerializer(serializers.ModelSerializer):

    calls = CallSerializer(many=True)
    contacts = ContactSerializer(many=True)
    locations = LocationSerializer(many=True)
    texts = TextSerializer(many=True)

    # TODO: update this
    datetime_last_update = serializers.SerializerMethodField()
    def get_datetime_last_update(self, phone):
        return models.get_utc_datetime_now()

    class Meta:
        model = Phone
        fields = [
            "uid",
            "device_id",
            "status",
            "name",
            "description",
            "mark",
            "phone_numbers",
            "calls",
            "contacts",
            "locations",
            "texts",
            "datetime_last_update",
        ]


class GetPhoneRecordingQueryParamSerializer(serializers.Serializer):
    phone_uid = serializers.UUIDField()


class UpdateNetworkSerializer(serializers.Serializer):

    # network_uid = serializers.UUIDField(required=True) just look up with auth user
    output_agol = serializers.NullBooleanField(required=False)
    output_kml = serializers.NullBooleanField(required=False)


class UpdatePhoneSerializer(serializers.Serializer):

    phone_uid = serializers.UUIDField(required=True)

    status = serializers.ChoiceField(
        choices=constants.JACKAL_PHONE_STATUSES, required=False
    )
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=255, required=False)
    mark = serializers.CharField(max_length=100, required=False)
    phone_numbers = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        return validate_unknown_attrs(attrs, self.initial_data, self.fields)


def validate_unknown_attrs(attrs, initial_data, fields):
    unknown = set(initial_data) - set(fields)
    if unknown:
        raise serializers.ValidationError(
            "Unknown field(s): {}".format(", ".join(unknown))
        )
    return attrs
