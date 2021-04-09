from datetime import datetime, timezone
from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from caracal.common.models import get_utc_datetime_now
from jackal.decorators import check_network_exists
from jackal.models import (
    Network,
    Phone,
    WhatsAppCall,
    WhatsAppGroup,
    WhatsAppMessage,
    WhatsAppUser,
)

from jackal.serializers import whatsapp as serializers
from jackal.views import utilities


class AddWhatsAppCallView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddWhatsAppCallSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        add_data = serializer.data
        device_id = add_data.pop("device_id")
        write_key = add_data.pop("write_key")
        user_jid_id = add_data.pop("user_jid_id")
        user_user_string = add_data.pop("user_user_string")
        datetime_recorded = add_data.pop("datetime_recorded", None)
        if datetime_recorded is None:
            timestamp_recorded = add_data.pop("timestamp_recorded")
            datetime_recorded = datetime.fromtimestamp(timestamp_recorded//1000).replace(tzinfo=timezone.utc)

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)
        whatsapp_user = _get_or_create_whatsapp_user(user_jid_id, user_user_string, phone, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        try:
            WhatsAppCall.objects.create(
                network=network, 
                phone=phone, 
                whatsapp_user=whatsapp_user, 
                datetime_recorded=datetime_recorded,
                **add_data
            )
        except IntegrityError:
            pass

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class AddWhatsAppGroupParticipantView(generics.GenericAPIView):
    
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddWhatsAppGroupParticipantSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        add_data = serializer.data
        device_id = add_data.pop("device_id")
        write_key = add_data.pop("write_key")
        group_jid_id = add_data.pop("group_jid_id")
        group_subject = add_data.pop("group_subject")
        group_user_string = add_data.pop("group_user_string")
        user_jid_id = add_data.pop("user_jid_id")
        user_user_string = add_data.pop("user_user_string")

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        whatsapp_group = _get_or_create_whatsapp_group(group_jid_id, group_user_string, phone, network)
        whatsapp_group.subject = group_subject
        whatsapp_group.save()

        whatsapp_user = _get_or_create_whatsapp_user(user_jid_id, user_user_string, phone, network)
        whatsapp_user.groups.add(whatsapp_group)

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class AddWhatsAppMessageView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddWhatsAppMessageSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        add_data = serializer.data
        device_id = add_data.pop("device_id")
        write_key = add_data.pop("write_key")
        group_jid_id = add_data.pop("group_jid_id", None)
        group_user_string = add_data.pop("group_user_string", None)
        user_jid_id = add_data.pop("user_jid_id", None)
        user_user_string = add_data.pop("user_user_string", None)
        datetime_recorded = add_data.pop("datetime_recorded", None)
        if datetime_recorded is None:
            timestamp_recorded = add_data.pop("timestamp_recorded")
            datetime_recorded = datetime.fromtimestamp(timestamp_recorded//1000).replace(tzinfo=timezone.utc)

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        whatsapp_group, whatsapp_user = None, None

        if group_jid_id and group_user_string:
           whatsapp_group = _get_or_create_whatsapp_group(group_jid_id, group_user_string, phone, network)

        if user_jid_id and user_user_string:
           whatsapp_user = _get_or_create_whatsapp_user(user_jid_id, user_user_string, phone, network)

        if whatsapp_group and whatsapp_user:
            whatsapp_user.groups.add(whatsapp_group)

        try:
            WhatsAppMessage.objects.create(
                network=network, 
                phone=phone, 
                whatsapp_group=whatsapp_group, 
                whatsapp_user=whatsapp_user, 
                datetime_recorded=datetime_recorded,
                **add_data
            )
        except IntegrityError:
            pass

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class AddWhatsAppUserView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddWhatsAppUserSerializer

    @check_network_exists
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        add_data = serializer.data
        device_id = add_data.pop("device_id")
        write_key = add_data.pop("write_key")
        user_jid_id = add_data.pop("user_jid_id")
        user_user_string = add_data.pop("user_user_string")

        network = Network.objects.get(write_key=write_key, is_active=True)
        phone = utilities.get_or_create_phone(device_id, network)

        phone.datetime_last_update = get_utc_datetime_now()
        phone.save()

        whatsapp_user = _get_or_create_whatsapp_user(user_jid_id, user_user_string, phone, network)

        return Response({"success": True}, status=status.HTTP_201_CREATED)


def _get_or_create_whatsapp_group(jid_id, user_string, phone, network):
    # in between first get and create, another request could have created the group so check again
    try:
        return WhatsAppGroup.objects.get(user_string=user_string, phone=phone)
    except WhatsAppGroup.DoesNotExist:
        try:
            return WhatsAppGroup.objects.create(jid_id=jid_id, user_string=user_string, phone=phone, network=network)
        except IntegrityError:
            return WhatsAppGroup.objects.get(user_string=user_string, phone=phone)


def _get_or_create_whatsapp_user(jid_id, user_string, phone, network):
    # in between first get and create, another request could have created the user so check again
    try:
        return WhatsAppUser.objects.get(user_string=user_string, phone=phone)
    except WhatsAppUser.DoesNotExist:
        try:
            return WhatsAppUser.objects.create(jid_id=jid_id, user_string=user_string, phone=phone, network=network)
        except IntegrityError:
            return WhatsAppUser.objects.get(user_string=user_string, phone=phone)
