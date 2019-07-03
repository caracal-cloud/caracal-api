

from django.conf import settings
from django.db.utils import IntegrityError
from django.utils import timezone
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import aws
from caracal.common.models import RealTimeAccount, RealTimeIndividual
import caracal.common.serializers as common_serializers

from collars import serializers as collar_serializers


class AddCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.AddCollarAccountSerializer

    def post(self, request):
        serializer = collar_serializers.AddCollarAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO: don't save creds to account, just use in rule...

        user = request.user
        data = serializer.data
        species = data['type']
        provider = data['provider']

        fetch_rule_input = dict()
        if provider == 'orbcomm':
            fetch_rule_input['orbcomm_timezone'] = data.pop('orbcomm_timezone')
            fetch_rule_input['orbcomm_company_id'] = data.pop('orbcomm_company_id')
        elif provider == 'savannah_tracking':
            fetch_rule_input['savannah_tracking_username'] = data.pop('savannah_tracking_username')
            fetch_rule_input['savannah_tracking_password'] = data.pop('savannah_tracking_password')

        try:
            account = RealTimeAccount.objects.create(organization=user.organization, source='collar', **data)
        except IntegrityError:
            return Response({
                'error': 'account_already_added',
                'message': 'account already added'
            }, status=status.HTTP_400_BAD_REQUEST)

        fetch_rule_input['account_uid'] = str(account.uid)


        """
        
        global_config = aws.get_global_config()


        fetch_function_name = 'caracal_%s_collars_fetch_%s' % (settings.STAGE.lower(), provider)
        fetch_lambda_function = aws.get_lambda_function(fetch_function_name)

        fetch_rule_name = aws.get_cloudwatch_fetch_collars_rule_name(user.organization.short_name, settings.STAGE,
                                                                     provider.short_name, species,
                                                                     collar_account.uid)

        aws.schedule_lambda_function(fetch_lambda_function['arn'], fetch_lambda_function['name'], fetch_rule_input,
                                     fetch_rule_name, global_config['COLLAR_FETCH_RATE_MINUTES'])

        create_kml_function_name = 'caracal_%s_collars_create_kml' % settings.STAGE.lower()
        create_kml_function = aws.get_lambda_function(create_kml_function_name)
        for period in global_config['PERIODS_HOURS']:
            create_kml_input = {
                'organization_uid': str(user.organization.uid),
                'species': species,
                'period_hours': period
            }
            create_kml_rule_name = aws.get_cloudwatch_create_kml_rule_name(user.organization.short_name,
                                                                           settings.STAGE, species, period)
            aws.schedule_lambda_function(create_kml_function['arn'], create_kml_function['name'], create_kml_input,
                                         create_kml_rule_name, global_config['COLLAR_KML_CREATE_RATE_MINUTES'])

        """

        message = f'{species} collar account added by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response({
            'account_uid': account.uid
        }, status=status.HTTP_201_CREATED)


class DeleteCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = common_serializers.DeleteAccountSerializer

    def post(self, request):
        serializer = common_serializers.DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = RealTimeAccount.objects.get(uid=serializer.data['account_uid'])
        except RealTimeAccount.DoesNotExist:
            return Response({
                'error': 'account_does_not_exist',
                'message': 'account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if account.organization != request.user.organization and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # doing this instead of .save() to avoid validate_unique error
        RealTimeAccount.objects.filter(uid=account.uid).update(datetime_updated=timezone.now(), is_active=False)

        # TODO: remove cloudwatch rules...

        return Response(status=status.HTTP_200_OK)


class GetCollarAccountsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.GetCollarAccountsSerializer

    def get_queryset(self):
        user = self.request.user
        return RealTimeAccount.objects.filter(is_active=True, organization=user.organization, source='collar')


class GetCollarAccountDetailView(generics.RetrieveAPIView):

    lookup_field = 'uid'
    serializer_class = collar_serializers.GetCollarAccountDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RealTimeAccount.objects.filter(organization=self.request.user.organization, source='collar')


class GetCollarIndividualsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.GetCollarIndividualsSerializer

    def get_queryset(self):

        serializer = common_serializers.GetRtIndividualsQueryParamsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        account_uid = serializer.data['account_uid']
        user = self.request.user

        try:
            account = RealTimeAccount.objects.get(is_active=True, organization=user.organization, uid=account_uid)
            if account.source != 'collar':
                return RealTimeIndividual.objects.none()
        except RealTimeAccount.DoesNotExist:
            return RealTimeIndividual.objects.none()

        return RealTimeIndividual.objects.filter(is_active=True, account=account)


class GetCollarIndividualDetailView(generics.RetrieveAPIView):

    lookup_field = 'uid'
    serializer_class = collar_serializers.GetCollarIndividualDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RealTimeIndividual.objects.filter(account__organization=self.request.user.organization)


class UpdateCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = common_serializers.UpdateRtAccountSerializer

    def post(self, request):
        serializer = common_serializers.UpdateRtAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        update_data = serializer.data
        account_uid = update_data.pop('account_uid')

        try:
            account = RealTimeAccount.objects.get(uid=account_uid)
        except RealTimeAccount.DoesNotExist:
            return Response({
                'error': 'rt_account_does_not_exist',
                'message': 'real-time account does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if account.organization != user.organization and not user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        RealTimeAccount.objects.filter(uid=account_uid).update(datetime_updated=timezone.now(), **update_data)

        message = f'{account.type} collar account updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


class UpdateCollarIndividualView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = collar_serializers.UpdateCollarIndividualSerializer

    def post(self, request):
        serializer = collar_serializers.UpdateCollarIndividualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        update_data = serializer.data
        individual_uid = update_data.pop('individual_uid')

        try:
            individual = RealTimeIndividual.objects.get(uid=individual_uid)
        except RealTimeIndividual.DoesNotExist:
            return Response({
                'error': 'rt_individual_does_not_exist',
                'message': 'real-time individual does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if individual.account.organization != user.organization and not user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        RealTimeIndividual.objects.filter(uid=individual_uid).update(datetime_updated=timezone.now(), **update_data)

        message = f'{individual.account.type} collar individual updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)














