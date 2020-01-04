
from datetime import datetime, timezone
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import stripe

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol
from caracal.common.aws_utils import kinesis
from caracal.common.models import get_num_sources
from custom_source import serializers
from custom_source import connections as source_connections
from custom_source.models import Device, Source
from outputs.models import AgolAccount


class AddRecordView(views.APIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.AddRecordSerializer

    def post(self, request):
        serializer = serializers.AddRecordSerializer(data=request.data)
        serializer.is_valid(True)

        device_id = serializer.data['device_id']
        write_key = serializer.data['write_key']

        try:
            source = Source.objects.get(write_key=write_key, is_active=True)
        except Source.DoesNotExist:
            return Response({
                'error': 'source_does_not_exist',
                'message': 'source account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        try: # this might be a bottleneck later on
            device = Device.objects.get(device_id=device_id, source=source)
        except Device.DoesNotExist:
            device = Device.objects.create(device_id=device_id, source=source)

        payload = {
            'device_id': device.pk,
            'source_id': source.pk,
            'datetime_recorded': serializer.data['datetime_recorded'],
            'lat': serializer.data['lat'],
            'lon': serializer.data['lon'],

            'alt_m': serializer.data.get('alt_m'),
            'speed_kmh': serializer.data.get('speed_kmh'),
            'temp_c': serializer.data.get('temp_c')
        }

        kinesis.put_firehose_record(payload, 'caracal_realtime_user') # fixme: move to env vars

        return Response(status=status.HTTP_201_CREATED)


class AddSourceView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddSourceSerializer

    def post(self, request):
        serializer = serializers.AddSourceSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        organization = user.organization

        data = serializer.validated_data

        num_sources = get_num_sources(organization) # unlimited source_limit is -1
        if 0 < organization.source_limit <= num_sources:
            return Response({
                'error': 'source_limit_reached',
                'message': 'You have reached the limit of your plan. Consider upgrading for unlimited sources.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # make sure user has an AGOL account set up and feature service exists
        agol_account = None
        if data.get('output_agol', False):
            agol_account = agol.verify_agol_state_and_get_account(user)
            if isinstance(agol_account, Response):
                return agol_account

        source = serializer.save(account=request.user)

        source_connections.schedule_source_outputs(data, source, user, agol_account=agol_account)

        return Response({
            'source_uid': source.uid,
            'write_key': source.write_key
        }, status=status.HTTP_201_CREATED)


class DeleteSourceView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteSourceSerializer

    def post(self, request):
        serializer = serializers.DeleteSourceSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user

        source_uid = serializer.data['source_uid']

        try:
            source = Source.objects.get(uid=source_uid)
        except Source.DoesNotExist:
            return Response({
                'error': 'source_does_not_exist',
                'message': 'source does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if source.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        source_connections.delete_source_kml(source)

        try: # if agol account exists, try to delete connection...
            agol_account = user.agol_account
        except AgolAccount.DoesNotExist:
            pass
        else:
            source_connections.delete_source_agol(agol_account=agol_account, source=source)

        source.is_active = False
        source.datetime_deleted = datetime.utcnow().replace(tzinfo=timezone.utc)
        source.save()

        return Response(status=status.HTTP_200_OK)


class GetDevicesView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetDevicesSerializer

    def get_queryset(self):

        serializer = serializers.GetDevicesQueryParamsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)

        source_uid = serializer.data['source_uid']
        user = self.request.user

        try:
            source = Source.objects.get(uid=source_uid, organization=user.organization, is_active=True)
        except Source.DoesNotExist:
            return Device.objects.none()

        return Device.objects.filter(source=source, is_active=True)


class GetDeviceDetailView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    lookup_field = 'uid'
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetDeviceDetailSerializer

    def get_queryset(self):
        organization = self.request.user.organization
        devices = Device.objects.filter(source__organization=organization, is_active=True)
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
    lookup_field = 'uid'
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
        device_uid = update_data.pop('device_uid')

        try:
            device = Device.objects.get(uid=device_uid, is_active=True)
        except Device.DoesNotExist:
            return Response({
                'error': 'device_does_not_exist'
            })

        if device.source.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        Device.objects.filter(uid=device_uid).update(datetime_updated=now, **update_data)

        message = f'custom source device ({device.device_id}) updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

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
        source_uid = update_data.pop('source_uid')

        if update_data.get('output_agol', False):
            try:
                AgolAccount.objects.get(account=user)
            except AgolAccount.DoesNotExist:
                return Response({
                    'error': 'agol_account_required',
                    'message': 'ArcGIS Online account required'
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            source = Source.objects.get(uid=source_uid, is_active=True)
        except Source.DoesNotExist:
            return Response({
                'error': 'source_does_not_exist',
                'message': 'source account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if source.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        update_data.pop('output_agol', None)
        update_data.pop('output_database', None)
        update_data.pop('output_kml', None)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        Source.objects.filter(uid=source_uid).update(datetime_updated=now, **update_data)

        source_connections.update_source_outputs(serializer.data, source, user)

        message = f'{source.name} custom source updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


