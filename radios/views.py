
from datetime import datetime, timezone
from rest_framework import permissions, status, generics
from rest_framework.response import Response
import uuid

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import agol, connections
from caracal.common.models import get_num_sources, RealTimeAccount, RealTimeIndividual
import caracal.common.serializers as common_serializers
from outputs.models import AgolAccount
from radios import serializers as radios_serializers


class AddAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = radios_serializers.AddAccountSerializer

    def post(self, request):
        serializer = radios_serializers.AddAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization

        data = serializer.data

        num_sources = get_num_sources(organization) # unlimited source_limit is -1
        if 0 < organization.source_limit <= num_sources:
            return Response({
                'error': 'source_limit_reached',
                'message': 'You have reached the limit of your plan. Consider upgrading for unlimited sources.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # make sure user has an AGOL account set up and feature service exists
        if data.get('output_agol', False):
            try:
                agol_account = AgolAccount.objects.get(account=user)
            except AgolAccount.DoesNotExist:
                return Response({
                    'error': 'agol_account_required',
                    'message': 'ArcGIS Online account required'
                }, status=status.HTTP_400_BAD_REQUEST)

        # enforce max number of accounts
        accounts = RealTimeAccount.objects.filter(organization=user.organization, source='radio', is_active=True)
        if accounts.count() > 5:
            return Response({
                'error': 'too_many_account',
                'message': 'max number of radio accounts is 5'
            }, status=status.HTTP_400_BAD_REQUEST)

        provider = 'TRBOnet' if data['provider'] == 'trbonet' else data['provider']
        title = f'Radios - {provider}' # default title

        radio_account = RealTimeAccount.objects.create(organization=user.organization, source='radio',
                                                 type=str(uuid.uuid4()), title=title)

        connections.schedule_realtime_outputs(data, radio_account.type, 'radio', radio_account, user, agol_account=agol_account)

        message = f'{provider} radio account added by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response({
            'account_uid': radio_account.uid
        }, status=status.HTTP_201_CREATED)


class AddPositionView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication] # todo: need to handle multiple tokens
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = radios_serializers.AddPositionSerializer

    def post(self, request):
        serializer = radios_serializers.AddPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(status=status.HTTP_201_CREATED)


class DeleteAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = common_serializers.DeleteAccountSerializer

    def post(self, request):
        serializer = common_serializers.DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        try:
            radio_account = RealTimeAccount.objects.get(uid=serializer.data['account_uid'], is_active=True)
        except RealTimeAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'radio account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if radio_account.organization != request.user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        connections.delete_realtime_kml(radio_account)

        try: # if agol account exists, try to delete connection...
            agol_account = user.agol_account
        except AgolAccount.DoesNotExist:
            pass
        else:
            connections.delete_realtime_agol(agol_account=agol_account, realtime_account=radio_account)

        radio_account.is_active = False
        radio_account.datetime_deleted = datetime.utcnow().replace(tzinfo=timezone.utc)
        radio_account.save()

        return Response(status=status.HTTP_200_OK)


class GetAccountsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = radios_serializers.GetRadioAccountsSerializer

    def get_queryset(self):
        user = self.request.user
        return RealTimeAccount.objects.filter(is_active=True, organization=user.organization, source='radio')


class GetRadioAccountDetailView(generics.RetrieveAPIView):

    lookup_field = 'uid'
    serializer_class = radios_serializers.GetRadioAccountDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RealTimeAccount.objects.filter(organization=self.request.user.organization, source='radio')


class GetRadioIndividualsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = radios_serializers.GetRadioIndividualsSerializer

    def get_queryset(self):

        serializer = common_serializers.GetRtIndividualsQueryParamsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        account_uid = serializer.data['account_uid']
        user = self.request.user

        try:
            account = RealTimeAccount.objects.get(is_active=True, organization=user.organization, uid=account_uid)
            if account.source != 'radio':
                return RealTimeIndividual.objects.none()
        except RealTimeAccount.DoesNotExist:
            return RealTimeIndividual.objects.none()

        return RealTimeIndividual.objects.filter(is_active=True, account=account)


class GetRadioIndividualDetailView(generics.RetrieveAPIView):

    lookup_field = 'uid'
    serializer_class = radios_serializers.GetRadioIndividualDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RealTimeIndividual.objects.filter(account__organization=self.request.user.organization)


class UpdateRadioAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = common_serializers.UpdateRtAccountSerializer

    def post(self, request):
        serializer = common_serializers.UpdateRtAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        update_data = serializer.data
        account_uid = update_data.pop('account_uid')

        if update_data.get('output_agol', False):
            try:
                agol_account = AgolAccount.objects.get(account=user)
            except AgolAccount.DoesNotExist:
                return Response({
                    'error': 'agol_account_required',
                    'message': 'ArcGIS Online account required'
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            radio_account = RealTimeAccount.objects.get(uid=account_uid, is_active=True)
        except RealTimeAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'radio account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if radio_account.organization != user.organization:
            return Response(status=status.HTTP_403_FORBIDDEN)

        provider = 'TRBOnet' if radio_account.provider == 'trbonet' else radio_account.provider

        update_data.pop('output_agol', None)
        update_data.pop('output_database', None)
        update_data.pop('output_kml', None)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        RealTimeAccount.objects.filter(uid=account_uid).update(datetime_updated=now, **update_data)

        connections.update_realtime_outputs(serializer.data, radio_account, user)

        message = f'{provider} radio account updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


class UpdateRadioIndividualView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = radios_serializers.UpdateRadioIndividualSerializer

    def post(self, request):
        serializer = radios_serializers.UpdateRadioIndividualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        update_data = serializer.data
        individual_uid = update_data.pop('individual_uid')

        try:
            individual = RealTimeIndividual.objects.get(uid=individual_uid, is_active=True)
        except RealTimeIndividual.DoesNotExist:
            return Response({
                'error': 'individual_does_not_exist',
                'message': 'individual does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if individual.account.organization != user.organization and not user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        RealTimeIndividual.objects.filter(uid=individual_uid).update(datetime_updated=now, **update_data)

        provider = 'TRBOnet' if individual.account.provider == 'trbonet' else individual.account.provider
        message = f'{provider} radio individual updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)



