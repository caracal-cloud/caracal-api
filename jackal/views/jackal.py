from datetime import datetime, timezone
from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import uuid

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol
from caracal.common.models import get_utc_datetime_now
from jackal import connections as jackal_connections
from jackal.decorators import check_network_exists
from jackal.models import (
    Call,
    Contact,
    Location,
    Log,
    Network,
    OtherPhone,
    Phone,
    Text,
)
from jackal.serializers import jackal as serializers
from jackal.views import utilities


# do not change the response format of add_*/ routes!

class AddCallView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddCallSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        add_data = serializer.data
        device_id = add_data.pop("device_id")
        write_key = add_data.pop("write_key")
        other_phone_number = add_data.pop("other_phone_number")
        datetime_recorded = add_data.pop("datetime_recorded", None)
        if datetime_recorded is None:
            timestamp_recorded = add_data.pop("timestamp_recorded")
            datetime_recorded = datetime.fromtimestamp(timestamp_recorded//1000).replace(tzinfo=timezone.utc)

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)
        other_phone = _get_or_create_other_phone(other_phone_number, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        try:
            Call.objects.create(
                network=network, 
                phone=phone, 
                other_phone=other_phone, 
                datetime_recorded=datetime_recorded,
                **add_data
            )
        except IntegrityError:
            pass

        try:
            Contact.objects.create(
                datetime_recorded=datetime_recorded,
                network=network, 
                phone=phone, 
                other_phone=other_phone
            )
        except IntegrityError:
            pass

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class AddContactView(generics.GenericAPIView):
    # this also supports updates
    # if the phone number has changed, a new entry will be created
    # if the name has changed, the entry will be updated

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddContactSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        d = serializer.data
        device_id, write_key, name, phone_number = (
            d["device_id"],
            d["write_key"],
            d["name"],
            d["phone_number"]
        )

        datetime_recorded = d.pop("datetime_recorded", None)
        if datetime_recorded is None:
            timestamp_recorded = d.pop("timestamp_recorded")
            datetime_recorded = datetime.fromtimestamp(timestamp_recorded//1000).replace(tzinfo=timezone.utc)

        phone_number = phone_number.replace(" ", "")
        phone_number = phone_number.replace("(", "")
        phone_number = phone_number.replace(")", "")
        phone_number = phone_number.replace("-", "")

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)
        other_phone = _get_or_create_other_phone(phone_number, network)

        # if the phone already has a name, add the previous one to aliases
        if other_phone.name:
            if other_phone.aliases:
                if other_phone.name not in other_phone.aliases.split(", "):
                    other_phone.aliases = other_phone.aliases + ", " + other_phone.name
            elif other_phone.name != name:
                other_phone.aliases = other_phone.name

        other_phone.name = name
        other_phone.save()

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        try:
            Contact.objects.create(
                datetime_recorded=datetime_recorded,
                network=network, 
                phone=phone, 
                other_phone=other_phone 
            )
        except IntegrityError as ie:
            pass

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class AddLocationView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddLocationSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(True)
        except:
            print(serializer.data)
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop("device_id")
        write_key = add_data.pop("write_key")
        datetime_recorded = add_data.pop("datetime_recorded", None)
        if datetime_recorded is None:
            timestamp_recorded = add_data.pop("timestamp_recorded")
            datetime_recorded = datetime.fromtimestamp(timestamp_recorded//1000).replace(tzinfo=timezone.utc)

        longitude = round(float(add_data.pop("longitude")), 6)
        latitude = round(float(add_data.pop("latitude")), 6)
        accuracy_m = round(float(add_data.pop("accuracy_m")), 2)

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        point = Point(longitude, latitude)

        try:
            Location.objects.create(
                phone=phone, 
                network=network, 
                position=point, 
                accuracy_m=accuracy_m,
                datetime_recorded=datetime_recorded,
                **add_data
            )
        except IntegrityError:
            pass

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class AddLogView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddLogSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        data = serializer.data
        device_id, write_key = data.pop('device_id'), data.pop('write_key')
        datetime_recorded = data.pop("datetime_recorded", None)
        if datetime_recorded is None:
            timestamp_recorded = data.pop("timestamp_recorded")
            datetime_recorded = datetime.fromtimestamp(timestamp_recorded//1000).replace(tzinfo=timezone.utc)

        network = Network.objects.get(write_key=write_key)
        phone = utilities.get_or_create_phone(device_id, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        try:
            Log.objects.create(network=network, phone=phone, datetime_recorded=datetime_recorded, **data)
        except IntegrityError as ie:
            print(ie)
            pass

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class AddTextView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddTextSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        add_data = serializer.data
        device_id = add_data.pop("device_id")
        write_key = add_data.pop("write_key")
        other_phone_number = add_data.pop("other_phone_number")
        datetime_recorded = add_data.pop("datetime_recorded", None)
        if datetime_recorded is None:
            timestamp_recorded = add_data.pop("timestamp_recorded")
            datetime_recorded = datetime.fromtimestamp(timestamp_recorded//1000).replace(tzinfo=timezone.utc)

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)
        other_phone = _get_or_create_other_phone(other_phone_number, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        try:
            Text.objects.create(
                network=network, 
                phone=phone, 
                other_phone=other_phone,
                datetime_recorded=datetime_recorded,
                **add_data
            )
        except IntegrityError:
            pass

        try:
            contact = Contact.objects.create(
                datetime_recorded=datetime_recorded,
                network=network, 
                phone=phone, 
                other_phone=other_phone
            )
        except IntegrityError as ie:
            pass

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class CreateNetworkView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.CreateNetworkSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        organization = user.organization
        data = serializer.validated_data

        try:
            network = organization.jackal_network
        except Network.DoesNotExist:
            write_key = str(uuid.uuid4()).replace("-", "")
            network = Network.objects.create(
                write_key=write_key, 
                organization=organization
            )

        if not network.cloudwatch_update_excel_rule_name:
            jackal_connections.schedule_jackal_excel(network, organization)

        if not network.cloudwatch_update_kml_rule_names:
            jackal_connections.schedule_jackal_kml(network, organization)

        return Response(
            {"write_key": network.write_key,}, status=status.HTTP_201_CREATED
        )


class GetCallsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.CallSerializer

    def get_queryset(self):
        return _get_recording_queryset(self.request, Call)


class GetContactsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ContactSerializer

    def get_queryset(self):
        return _get_recording_queryset(self.request, Contact)


class GetLocationsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.LocationSerializer

    def get_queryset(self):
        return _get_recording_queryset(self.request, Location)


class GetTextsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.TextSerializer

    def get_queryset(self):
        return _get_recording_queryset(self.request, Text)


class GetNetworkView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetNetworkSerializer

    def get_object(self):
        organization = self.request.user.organization
        try:
            return organization.jackal_network
        except Network.DoesNotExist:
            return None


class GetPhonesView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetPhonesSerializer

    def get_queryset(self):
        network = self.request.user.organization.jackal_network
        try:
            return Phone.objects.filter(network=network, is_active=True)
        except Network.DoesNotExist:
            return Phone.objects.none()


class GetPhoneDetailView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    lookup_field = "uid"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetPhoneDetailSerializer

    def get_queryset(self):
        network = self.request.user.organization.jackal_network
        try:
            return Phone.objects.filter(network=network, is_active=True)
        except Network.DoesNotExist:
            return Phone.objects.none()


class UpdateNetworkView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateNetworkSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        try:
            network = user.organization.jackal_network
        except Network.DoesNotExist:
            return Response({
                'error': 'network_not_found',
                'message': 'a network was not found'
            }, status=status.HTTP_400_BAD_REQUEST)

        update_data = serializer.data

        if update_data.get("output_agol", False):
            try:
                agol_account = user.agol_account
            except AgolAccount.DoesNotExist:
                return Response({
                    "error": "agol_account_required",
                    "message": "ArcGIS Online account required",
                },status=status.HTTP_400_BAD_REQUEST)

        jackal_connections.update_jackal_outputs(serializer.data, network, user)

        message = f"Jackal account updated by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(status=status.HTTP_200_OK)


class UpdatePhoneView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdatePhoneSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        user = request.user

        update_data = serializer.data
        phone_uid = update_data.pop("phone_uid")

        try:
            phone = Phone.objects.get(uid=phone_uid, is_active=True)
        except Phone.DoesNotExist:
            return Response(
                {
                    "error": "phone_does_not_exist",
                    "message": "Jackal phone does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if phone.network.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        agol_connection = phone.network.connections.filter(
            agol_account__isnull=False
        ).first()
        if agol_connection is not None:

            attributes = dict()
            if "name" in update_data and update_data["name"] != phone.name:
                attributes["Name"] = update_data["name"]

            if len(attributes) > 0:

                agol_account = agol_connection.agol_account

                # TODO: this is grossly inefficient, but AGOL doesn't seem to have an update with where clause

                features = agol.get_jackal_features(
                    agol_account=agol_account,
                    device_id=phone.device_id,
                    layer_id=agol_connection.agol_layer_id,
                )

                print(f"Updating {len(features)} features")
                updates = [(f.id, attributes, None) for f in features]

                agol.update_features(
                    agol_account=agol_account,
                    layer_id=agol_connection.agol_layer_id,
                    updates=updates,
                )

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        Phone.objects.filter(uid=phone_uid).update(datetime_updated=now, **update_data)

        message = f"Jackal phone updated by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(status=status.HTTP_200_OK)


def _get_or_create_other_phone(phone_number, network):
    # in between first get and create, another request could have created the other-phone so check again
    try:
        return OtherPhone.objects.get(network=network, phone_number=phone_number)
    except OtherPhone.DoesNotExist:
        try:
            return OtherPhone.objects.create(network=network, phone_number=phone_number)
        except IntegrityError:
            return OtherPhone.objects.get(network=network, phone_number=phone_number)


def _get_recording_queryset(request, _class):

    serializer = serializers.GetPhoneRecordingQueryParamSerializer(
        data=request.query_params
    )
    serializer.is_valid(raise_exception=True)
    phone_uid = serializer.data["phone_uid"]

    try:
        phone = Phone.objects.get(uid=phone_uid)
    except Phone.DoesNotExist:
        return _class.objects.none()

    if phone.network.organization != request.user.organization:
        return _class.objects.none()

    return _class.objects.filter(phone=phone)
