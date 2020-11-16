from datetime import datetime, timezone
from django.conf import settings
from django.contrib.gis.geos import Point
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import stripe

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol
from caracal.common.aws_utils import kinesis
from caracal.common.models import get_num_sources
from caracal.common.decorators import check_agol_account_connected, check_source_limit
from custom_source import serializers
from custom_source import connections as source_connections
from custom_source.models import Device, Record, Source
from outputs.models import AgolAccount


class AddRecordView(views.APIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddRecordSerializer

    def post(self, request):
        serializer = serializers.AddRecordSerializer(data=request.data)
        serializer.is_valid(True)

        device_id = serializer.data["device_id"]
        write_key = serializer.data["write_key"]

        try:
            source = Source.objects.get(write_key=write_key, is_active=True)
        except Source.DoesNotExist:
            return Response(
                {
                    "error": "source_does_not_exist",
                    "message": "source account does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:  # this might be a bottleneck later on
            device = Device.objects.get(device_id=device_id, source=source)
        except Device.DoesNotExist:
            device = Device.objects.create(device_id=device_id, source=source)

        datetime_recorded = serializer.data["datetime_recorded"]
        lat = round(float(serializer.data["lat"]), 6)
        lon = round(float(serializer.data["lon"]), 6)
        alt_m = round(float(serializer.data.get("alt_m")), 2)
        speed_kmh = round(float(serializer.data.get("speed_kmh")), 2)
        temp_c = round(float(serializer.data.get("temp_c")), 2)

        payload = {
            "device_id": device.pk,
            "source_id": source.pk,
            "datetime_recorded": datetime_recorded,
            "lat": lat,
            "lon": lon,
            "alt_m": alt_m,
            "speed_kmh": speed_kmh,
            "temp_c": temp_c,
        }

        if settings.STAGE in ["testing", "development"]:
            position = Point(lon, lat, srid=settings.SRID)   
            Record.objects.create(
                source=source, 
                device=device, 
                position=position,
                datetime_recorded=datetime_recorded,
                alt_m=alt_m,
                speed_kmh=speed_kmh,
                temp_c=temp_c
            )

        else:
            kinesis.put_firehose_record(
                payload, "caracal_realtime_user"
            )  # fixme: move to env vars

        return Response(status=status.HTTP_201_CREATED)


class AddSourceView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddSourceSerializer

    @check_source_limit
    @check_agol_account_connected
    def post(self, request):
        serializer = serializers.AddSourceSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        organization = user.organization

        data = serializer.validated_data

        source = serializer.save(account=request.user)

        agol_account = user.agol_account if hasattr(user, "agol_account") else None
        source_connections.schedule_source_outputs(
            data=data, source=source, 
            user=user, agol_account=agol_account
        )

        return Response(
            {"source_uid": source.uid, "write_key": source.write_key},
            status=status.HTTP_201_CREATED,
        )


class DeleteSourceView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteSourceSerializer

    def post(self, request):
        serializer = serializers.DeleteSourceSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        source_uid = serializer.data["source_uid"]

        try:
            source = Source.objects.get(uid=source_uid)
        except Source.DoesNotExist:
            return Response(
                {"error": "source_does_not_exist", "message": "source does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if source.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        source_connections.delete_source_kml(source)

        try:  # if agol account exists, try to delete connection...
            agol_account = user.agol_account
        except AgolAccount.DoesNotExist:
            pass
        else:
            source_connections.delete_source_agol(
                agol_account=agol_account, source=source
            )

        source.is_active = False
        source.datetime_deleted = datetime.utcnow().replace(tzinfo=timezone.utc)
        source.save()

        return Response(status=status.HTTP_200_OK)


class GetDevicesView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetDevicesSerializer

    def get_queryset(self):

        serializer = serializers.GetDevicesQueryParamsSerializer(
            data=self.request.query_params
        )
        serializer.is_valid(raise_exception=True)

        source_uid = serializer.data["source_uid"]
        user = self.request.user

        try:
            source = Source.objects.get(
                uid=source_uid, organization=user.organization, is_active=True
            )
        except Source.DoesNotExist:
            return Device.objects.none()

        return Device.objects.filter(source=source, is_active=True)


class GetDeviceDetailView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    lookup_field = "uid"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetDeviceDetailSerializer

    def get_queryset(self):
        organization = self.request.user.organization
        devices = Device.objects.filter(
            source__organization=organization, is_active=True
        )
        return devices


class GetSourcesView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetSourcesSerializer

    def get_queryset(self):
        organization = self.request.user.organization
        sources = Source.objects.filter(organization=organization, is_active=True)
        return sources


class GetSourceDetailView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    lookup_field = "uid"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetSourceDetailSerializer

    def get_queryset(self):
        organization = self.request.user.organization
        sources = Source.objects.filter(organization=organization, is_active=True)
        return sources


class UpdateDeviceView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateDeviceSerializer

    def post(self, request):
        serializer = serializers.UpdateDeviceSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user

        update_data = serializer.data
        device_uid = update_data.pop("device_uid")

        try:
            device = Device.objects.get(uid=device_uid, is_active=True)
        except Device.DoesNotExist:
            return Response({"error": "device_does_not_exist"})

        if device.source.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # do this before updating device so we know old values
        # if there is a connected AGOL layer, update features in the layer on device_id
        # this should just return one connection...
        agol_connections = device.source.connections.filter(
            agol_account__isnull=False
        )
        for agol_connection in agol_connections:

            attributes = dict()
            if "name" in update_data and update_data["name"] != device.name:
                attributes["Name"] = update_data["name"]

            if len(attributes) > 0:

                agol_account = agol_connection.agol_account

                # TODO: this is grossly inefficient, but AGOL doesn't seem to have an update with where clause

                features = agol.get_custom_source_features(
                    agol_account=agol_account,
                    device_id=device.device_id,
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
        Device.objects.filter(uid=device_uid).update(
            datetime_updated=now, **update_data
        )

        message = f"custom source device ({device.device_id}) updated by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(status=status.HTTP_200_OK)


class UpdateSourceView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateSourceSerializer

    def post(self, request):
        serializer = serializers.UpdateSourceSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user

        update_data = serializer.data
        source_uid = update_data.pop("source_uid")

        if update_data.get("output_agol", False):
            try:
                agol_account = AgolAccount.objects.get(account=user)
            except AgolAccount.DoesNotExist:
                return Response(
                    {
                        "error": "agol_account_required",
                        "message": "ArcGIS Online account required",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            source = Source.objects.get(uid=source_uid, is_active=True)
        except Source.DoesNotExist:
            return Response(
                {
                    "error": "source_does_not_exist",
                    "message": "source account does not exist",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if source.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        update_data.pop("output_agol", None)
        update_data.pop("output_kml", None)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        Source.objects.filter(uid=source_uid).update(
            datetime_updated=now, **update_data
        )

        source_connections.update_source_outputs(serializer.data, source, user)

        message = f"{source.name} custom source updated by {user.name}"
        ActivityChange.objects.create(
            organization=user.organization, account=user, message=message
        )

        return Response(status=status.HTTP_200_OK)
