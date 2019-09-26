
from datetime import datetime, timezone
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import stripe

from account.models import Account, Organization
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common.aws import put_firehose_record
from caracal.common.models import get_num_sources
from custom_source import serializers
from custom_source.models import Source


class AddSourceView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddSourceSerializer

    def post(self, request):
        serializer = serializers.AddSourceSerializer(data=request.data)
        serializer.is_valid(True)

        organization = request.user.organization

        num_sources = get_num_sources(organization) # unlimited source_limit is -1
        if 0 < organization.source_limit <= num_sources:
            return Response({
                'error': 'source_limit_reached',
                'message': 'You have reached the limit of your plan. Consider upgrading for unlimited sources.'
            }, status=status.HTTP_400_BAD_REQUEST)

        source = serializer.save(account=request.user)

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

        source.is_active = False
        source.save()

        # TODO: remove destinations...

        return Response(status=status.HTTP_200_OK)


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

        try:
            source = Source.objects.get(uid=source_uid, is_active=True)
        except Source.DoesNotExist:
            return Response({
                'error': 'source_does_not_exist',
                'message': 'source account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if source.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        Source.objects.filter(uid=source_uid).update(datetime_updated=now, **update_data)

        message = f'{source.name} custom source updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


class TempAddRecordView(views.APIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.TempAddRecordSerializer

    def post(self, request):
        serializer = serializers.TempAddRecordSerializer(data=request.data)
        serializer.is_valid(True)

        try:
            source = Source.objects.get(write_key=serializer.data['write_key'], is_active=True)
        except Source.DoesNotExist:
            return Response({
                'error': 'source_does_not_exist',
                'message': 'source account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            'source_id': source.pk,
            'datetime_recorded': serializer.data['datetime_recorded'],
            'lat': serializer.data['lat'],
            'lon': serializer.data['lon'],

            'alt_m': serializer.data.get('alt_m'),
            'device_id': serializer.data.get('device_id'),
            'speed_kmh': serializer.data.get('speed_kmh'),
            'temp_c': serializer.data.get('temp_c')
        }

        put_firehose_record(payload, 'caracal_realtime_user')

        return Response(status=status.HTTP_200_OK)

