
from django.utils import timezone
import json
from rest_framework import permissions, status, generics
from rest_framework.response import Response
import uuid

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import connections
from caracal.common.fields import get_updated_outputs
from caracal.common.models import get_num_sources, RealTimeAccount, RealTimeIndividual
import caracal.common.serializers as common_serializers
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

        num_sources = get_num_sources(organization) # unlimited source_limit is -1
        if 0 < organization.source_limit <= num_sources:
            return Response({
                'error': 'source_limit_reached',
                'message': 'You have reached the limit of your plan. Consider upgrading for unlimited sources.'
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.data

        # enforce max number of accounts
        accounts = RealTimeAccount.objects.filter(organization=user.organization, source='radio', is_active=True)
        if accounts.count() > 5:
            return Response({
                'error': 'too_many_account',
                'message': 'max number of radio accounts is 5'
            }, status=status.HTTP_400_BAD_REQUEST)


        provider = data['provider']
        if provider == 'trbonet':
            provider = 'TRBOnet'

        outputs = {
            'output_agol': data.pop('output_agol', False),
            'output_database': data.pop('output_database', False),
            'output_kml': data.pop('output_kml', False)
        }
        outputs = json.dumps(outputs)

        title = f'Radios - {provider}' # default title

        account = RealTimeAccount.objects.create(organization=user.organization, source='radio',
                                                 type=str(uuid.uuid4()),
                                                 outputs=outputs, title=title, **data)

        connections.create_connections(organization, serializer.data, {'realtime_account': account})

        message = f'{provider} radio account added by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response({
            'account_uid': account.uid
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

        try:
            account = RealTimeAccount.objects.get(uid=serializer.data['account_uid'], is_active=True)
        except RealTimeAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'radio account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if account.organization != request.user.organization and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        RealTimeAccount.objects.filter(uid=account.uid).update(datetime_updated=timezone.now(), is_active=False)

        connections.delete_connections(account)

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
        organization = user.organization

        update_data = serializer.data
        account_uid = update_data.pop('account_uid')

        try:
            account = RealTimeAccount.objects.get(uid=account_uid, is_active=True)
        except RealTimeAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'radio account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if account.organization != user.organization and not user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        outputs = get_updated_outputs(account, update_data)

        provider = 'TRBOnet' if account.provider == 'trbonet' else account.provider

        RealTimeAccount.objects.filter(uid=account_uid).update(datetime_updated=timezone.now(),
                                                               outputs=outputs, **update_data)

        connections.update_connections(organization, serializer.data, {'realtime_account': account})

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

        RealTimeIndividual.objects.filter(uid=individual_uid).update(datetime_updated=timezone.now(), **update_data)

        provider = 'TRBOnet' if individual.account.provider == 'trbonet' else individual.account.provider
        message = f'{provider} radio individual updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)



