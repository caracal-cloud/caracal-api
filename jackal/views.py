

from datetime import datetime, timezone
from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import uuid

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol
from jackal import connections, serializers
from jackal.decorators import check_network_exists
from jackal.models import Call, Contact, Location, Network, OtherPhone, Phone, Text


class AddCallView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddCallSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        # TODO: this is for debugging purposes, later change to is_valid(True)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        other_phone_number = add_data.pop('other_phone_number')

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = _get_or_create_phone(device_id, network)
        other_phone = _get_or_create_other_phone(other_phone_number, network)

        try:
            Call.objects.create(network=network, phone=phone, other_phone=other_phone, **add_data)
        except IntegrityError:
            pass

        return Response({
            'success': True
        }, status=status.HTTP_201_CREATED)


class AddContactView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddContactSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        # TODO: this is for debugging purposes, later change to is_valid(True)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        name = add_data.pop('name')

        phone_number = add_data.pop('phone_number')
        phone_number = phone_number.replace(' ', '')
        phone_number = phone_number.replace('(', '')
        phone_number = phone_number.replace(')', '')
        phone_number = phone_number.replace('-', '')

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = _get_or_create_phone(device_id, network)
        other_phone = _get_or_create_other_phone(phone_number, network)

        other_phone.name = name
        other_phone.save()

        try:
            Contact.objects.create(network=phone.network, phone=phone, other_phone=other_phone, **add_data)
        except IntegrityError: # fixme: this is always throwing
            print('integrity')
            pass

        return Response({
            'success': True
        }, status=status.HTTP_201_CREATED)


class AddLocationView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddLocationSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        # TODO: this is for debugging purposes, later change to is_valid(True)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        longitude = round(float(add_data.pop('longitude')), 6)
        latitude = round(float(add_data.pop('latitude')), 6)

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = _get_or_create_phone(device_id, network)

        point = Point(longitude, latitude)

        try:
            Location.objects.create(phone=phone, network=network, position=point, **add_data)
        except IntegrityError:
            pass

        return Response({
            'success': True
        }, status=status.HTTP_201_CREATED)


class AddTextView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddTextSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        # TODO: this is for debugging purposes, later change to is_valid(True)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        other_phone_number = add_data.pop('other_phone_number')

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = _get_or_create_phone(device_id, network)
        other_phone = _get_or_create_other_phone(other_phone_number, network)

        try:
            Text.objects.create(network=phone.network, phone=phone, other_phone=other_phone, **add_data)
        except IntegrityError:
            pass

        return Response({
            'success': True
        }, status=status.HTTP_201_CREATED)


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
            return Response({
                'error': 'network_already_created',
                'message': 'Jackal network already created'
            }, status=status.HTTP_400_BAD_REQUEST)
        except:
            # create a new network
            write_key = str(uuid.uuid4()).replace('-', '')
            network = Network.objects.create(write_key=write_key, organization=organization)

        agol_account = user.agol_account if hasattr(user, "agol_account") else None
        connections.schedule_jackal_outputs(
            data=data,
            network=network,
            user=user,
            agol_account=agol_account
        )

        return Response({
            'write_key': network.write_key,
        }, status=status.HTTP_201_CREATED)


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
    lookup_field = 'uid'
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
        phone_uid = update_data.pop('phone_uid')

        try:
            phone = Phone.objects.get(uid=phone_uid, is_active=True)
        except Phone.DoesNotExist:
            return Response({
                'error': 'phone_does_not_exist',
                'message': 'Jackal phone does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if phone.network.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        agol_connection = phone.network.connections.filter(agol_account__isnull=False).first()
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
                    layer_id=agol_connection.agol_layer_id
                )

                print(f'Updating {len(features)} features')
                updates = [(f.id, attributes, None) for f in features]  

                agol.update_features(
                    agol_account=agol_account,
                    layer_id=agol_connection.agol_layer_id,
                    updates=updates
                )

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        Phone.objects.filter(uid=phone_uid).update(datetime_updated=now, **update_data)

        message = f'Jackal phone updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


def _get_or_create_phone(device_id, network):
    try:
        return Phone.objects.get(device_id=device_id, network=network, is_active=True)
    except Phone.DoesNotExist:
        return Phone.objects.create(device_id=device_id, network=network)


def _get_or_create_other_phone(phone_number, network):
    try:
        return OtherPhone.objects.get(network=network, phone_number=phone_number, is_active=True)
    except OtherPhone.DoesNotExist:
        return OtherPhone.objects.create(network=network, phone_number=phone_number)


def _get_recording_queryset(request, _class):

        serializer = serializers.GetPhoneRecordingQueryParamSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        phone_uid = serializer.data['phone_uid']

        try:
            phone = Phone.objects.get(uid=phone_uid)
        except:
            return _class.objects.none()

        if phone.network.organization != request.user.organization:
            return _class.objects.none()

        return _class.objects.filter(phone=phone)
