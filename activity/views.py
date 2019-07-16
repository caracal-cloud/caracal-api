
from datetime import timedelta
from django.utils import timezone
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from activity import serializers
from activity.models import ActivityAlert, ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common.models import RealTimePositionHash


class DeleteAlertView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteAlertSerializer

    def post(self, request):
        serializer = serializers.DeleteAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            alert = ActivityAlert.objects.get(uid=serializer.data['uid'])
        except ActivityAlert.DoesNotExist:
            return Response({
                'error': 'alert_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if alert.organization != request.user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        alert.is_active = False
        alert.save()

        return Response(status=status.HTTP_200_OK)


class GetEventsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetEventsSerializer

    def get_queryset(self):
        #user = self.request.user
        #return ActivityAlert.objects.filter(is_active=True, organization=user.organization)

        # todo: this is temporary
        from account.models import Account
        superuser = Account.objects.get(is_superuser=True)
        return ActivityAlert.objects.filter(is_active=True, organization=superuser.organization)


class GetChangesView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetChangesSerializer

    def get_queryset(self):
        #user = self.request.user
        #return ActivityChange.objects.filter(is_active=True, organization=user.organization)

        # todo: this is temporary
        from account.models import Account
        superuser = Account.objects.get(is_superuser=True)
        return ActivityChange.objects.filter(is_active=True, organization=superuser.organization)


class GetOverviewMetricsView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        organization = user.organization

        period = request.query_params.get('period', 'day')
        if period == 'day':
            hours = 24
        elif period == 'week':
            hours = 168
        elif period == 'month':
            hours = 720
        else:
            hours = 24

        then = timezone.now() - timedelta(hours=hours)

        data = {}

        # Collars
        accounts = organization.rt_accounts.filter(is_active=True)
        for account in accounts:
            key = f'num_{account.type}_positions'
            # initialize and increment number of positions grouped by type (elephant, radio, etc.)
            if key not in data.keys():
                data[key] = 0
            data[key] += RealTimePositionHash.objects.filter(account=account, datetime_recorded__gte=then).count()

        # Alerts
        data['num_alerts'] = organization.alerts.count()

        return Response(status=status.HTTP_200_OK, data=data)