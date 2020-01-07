

from datetime import datetime, timezone
from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import uuid

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from jackal import serializers
from jackal.models import Call, Contact, Location, Network, OtherPhone, Phone, Text


def get_phone_or_response(device_id, write_key):

    try:
        network = Network.objects.get(write_key=write_key, is_active=True)
    except Network.DoesNotExist:
        return Response({
            'error': 'network_does_not_exist',
            'message': 'Jackal network does not exist or write key is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        return Phone.objects.get(device_id=device_id, network=network)
    except Phone.DoesNotExist:
        return Phone.objects.create(device_id=device_id, network=network)


class AddCallView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddCallSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        other_phone_number = add_data.pop('other_phone_number')

        phone = get_phone_or_response(device_id, write_key)
        if isinstance(phone, Response):
            return phone

        try:
            other_phone = OtherPhone.objects.get(network=phone.network, phone_number=other_phone_number)
        except OtherPhone.DoesNotExist:
            other_phone = OtherPhone.objects.create(network=phone.network, phone_number=other_phone_number)

        try:
            Call.objects.create(network=phone.network, phone=phone, other_phone=other_phone, **add_data)
        except IntegrityError:
            pass

        return Response({
            'success': True
        }, status=status.HTTP_201_CREATED)


class AddContactView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddContactSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        phone_number = add_data.pop('phone_number')
        name = add_data.pop('name')

        phone = get_phone_or_response(device_id, write_key)
        if isinstance(phone, Response):
            return phone

        try:
            other_phone = OtherPhone.objects.get(network=phone.network, phone_number=phone_number)
            other_phone.name = name
            other_phone.save()
        except:
            other_phone = OtherPhone.objects.create(network=phone.network, phone_number=phone_number, name=name)

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

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        longitude = float(add_data.pop('longitude'))
        latitude = float(add_data.pop('latitude'))

        phone = get_phone_or_response(device_id, write_key)
        if isinstance(phone, Response):
            return phone

        point = Point(longitude, latitude)

        try:
            Location.objects.create(phone=phone, network=phone.network, position=point, **add_data)
        except IntegrityError:
            pass

        return Response({
            'success': True
        }, status=status.HTTP_201_CREATED)


class AddTextView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddTextSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(False)
        except:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        add_data = serializer.data
        device_id = add_data.pop('device_id')
        write_key = add_data.pop('write_key')
        other_phone_number = add_data.pop('other_phone_number')

        phone = get_phone_or_response(device_id, write_key)
        if isinstance(phone, Response):
            return phone

        try:
            other_phone = OtherPhone.objects.get(network=phone.network, phone_number=other_phone_number)
        except OtherPhone.DoesNotExist:
            other_phone = OtherPhone.objects.create(network=phone.network, phone_number=other_phone_number)

        try:
            Text.objects.create(network=phone.network, phone=phone, other_phone=other_phone, **add_data)
        except IntegrityError:
            pass


        return Response({
            'success': True
        }, status=status.HTTP_201_CREATED)


class CreateNetworkView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        organization = request.user.organization

        try:
            network = organization.jackal_network
            return Response({
                'error': 'network_already_created',
                'message': 'Jackal network already created'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Network.DoesNotExist:
            write_key = str(uuid.uuid4()).replace('-', '')
            network = Network.objects.create(write_key=write_key, organization=organization)

        return Response({
            'write_key': network.write_key,
        }, status=status.HTTP_201_CREATED)



class GetCallsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.CallSerializer

    def get_queryset(self):
        return get_recording_queryset(self.request, Call)


class GetContactsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ContactSerializer

    def get_queryset(self):
        return get_recording_queryset(self.request, Contact)


class GetLocationsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.LocationSerializer

    def get_queryset(self):
        return get_recording_queryset(self.request, Location)


class GetTextsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.TextSerializer

    def get_queryset(self):
        return get_recording_queryset(self.request, Text)


def get_recording_queryset(request, _class):
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


class GetPhonesView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetPhonesSerializer

    def get_queryset(self):
        try:
            return Phone.objects.filter(network=self.request.user.organization.jackal_network, is_active=True)
        except Network.DoesNotExist:
            return Phone.objects.none()


class GetPhoneDetailView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    lookup_field = 'uid'
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetPhoneDetailSerializer

    def get_queryset(self):
        try:
            return Phone.objects.filter(network=self.request.user.organization.jackal_network, is_active=True)
        except Network.DoesNotExist:
            return Phone.objects.none()


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

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        Phone.objects.filter(uid=phone_uid).update(datetime_updated=now, **update_data)

        message = f'Jackal phone updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


