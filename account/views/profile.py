
from datetime import datetime, timedelta, timezone
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from account import serializers
from account.models import Account
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import stripe_utils

class ForceOrganizationUpdateView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ForceOrganizationUpdateSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: '',
    }, security=[settings.SWAGGER_SETTINGS['SECURITY_DEFINITIONS']], operation_id='account - force organization update')
    def post(self, request):
        user = request.user

        if not user.organization.update_required:
            return Response({
                'error': 'update_not_required'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = serializers.ForceOrganizationUpdateSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(status=status.HTTP_200_OK)


class GetProfileView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetProfileSerializer

    def get_object(self):
        return self.request.user


class GetAccountStatusView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        user = request.user
        organization = user.organization
        subscription_status = organization.stripe_subscription_status

        data = {
            'status_message': None,
            'status_level': None,
            'status_link_to_text': None,
            'status_link_to_page': None # Upgrade plan, Update payment method,
        }

        subscription = stripe_utils.get_subscription(organization.stripe_subscription_id)

        if subscription['status'] == 'active':
            data['status_message'] = None
            data['status_level'] = None

        elif subscription['status'] == 'trialing':

            data['status_link_to_text'] = 'Upgrade'
            data['status_link_to_page'] = 'select_plan_and_pay'

            trial_timedelta = subscription['trial_end'] - datetime.utcnow().replace(tzinfo=timezone.utc)

            if trial_timedelta.days == 0:
                trial_hours = trial_timedelta.seconds // 3600
                if trial_hours == 0:
                    data['status_message'] = 'Your trial expires in less than 1 hour.'
                elif trial_hours == 1:
                    data['status_message'] = 'Your trial expires in 1 hour.'
                else:
                    data['status_message'] = f'Your trial expires in {trial_hours} hours.'
                data['status_level'] = 'danger'

            elif trial_timedelta.days == 1:
                data['status_message'] = 'Your trial expires in 1 day.'
                data['status_level'] = 'danger'

            else:
                data['status_message'] = f'Your trial expires in {trial_timedelta.days} days.'
                data['status_level'] = 'warning' if trial_timedelta.days <= 5 else 'info'

        return Response(data, status=status.HTTP_200_OK)


class UpdateAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateAccountSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: '',
    }, security=[settings.SWAGGER_SETTINGS['SECURITY_DEFINITIONS']], operation_id='account - update account')
    def post(self, request):
        user = request.user
        if user.is_demo:
            return Response(status=status.HTTP_200_OK)

        serializer = serializers.UpdateAccountSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)

        if 'logo' in serializer.validated_data.keys() and user.organization.update_required:
            return Response({
                'error': 'organization_update_required',
                'message': 'organization update required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # only admin can update organization
        admin_fields = {'organization_name', 'timezone', 'logo'}
        serializer_fields = set(serializer.validated_data.keys())
        if len(admin_fields.intersection(serializer_fields)) > 0:
            if not user.is_admin:
                return Response({
                    'error': 'admin_privileges_required'
                }, status=status.HTTP_403_FORBIDDEN)
            else:
                message = f'organization profile updated by {user.name}'
                ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        serializer.save()

        return Response(status=status.HTTP_200_OK)




