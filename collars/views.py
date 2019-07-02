
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.utils import IntegrityError
import json
from rest_framework import permissions, status, generics
from rest_framework.response import Response
import sentry_sdk
import traceback

from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import aws
from collars import serializers
from collars.models import CollarAccount, CollarIndividual, CollarProvider


class AddCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddCollarAccountSerializer

    def post(self, request):
        serializer = serializers.AddCollarAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO: don't save creds to account, just use in rule...

        # fixme: possibly not enforcing uniqueness

        global_config = aws.get_global_config()

        user = request.user
        data = serializer.data
        species = data['species']
        provider_short_name = data.pop('provider_short_name')

        try:
            provider = CollarProvider.objects.get(short_name=provider_short_name, is_available=True)
        except CollarProvider.DoesNotExist:
            return Response({
                'error': 'unknown_provider'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            collar_account = CollarAccount.objects.create(organization=request.user.organization, provider=provider, **data)
        except ValidationError:
            return Response({
                'error': 'account_already_added'
            }, status=status.HTTP_400_BAD_REQUEST)

        """
        fetch_function_name = 'caracal_%s_collars_fetch_%s' % (settings.STAGE.lower(), provider.short_name)
        fetch_lambda_function = aws.get_lambda_function(fetch_function_name)

        fetch_rule_input = {
            'collar_account_uid': str(collar_account.uid),
            'organization_uid': str(user.organization.uid),
            'species': species
        }

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
            'collar_account_uid': collar_account.collar_account_uid
        }, status=status.HTTP_201_CREATED)


class DeleteCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteCollarAccountSerializer

    def post(self, request):
        serializer = serializers.DeleteCollarAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            collar_account = CollarAccount.objects.get(uid=serializer.data['collar_account_uid'])
        except CollarAccount.DoesNotExist:
            return Response({
                'error': 'collar_account_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if collar_account.organization != request.user.organization and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # doing this instead of .save() to avoid validate_unique error
        CollarAccount.objects.filter(uid=collar_account.uid).update(datetime_updated=timezone.now(), is_active=False)

        # TODO: remove cloudwatch rules...

        return Response(status=status.HTTP_200_OK)


class GetCollarAccountsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetCollarAccountsSerializer

    def get_queryset(self):
        user = self.request.user
        return CollarAccount.objects.filter(is_active=True, organization=user.organization)


class GetCollarAccountDetailView(generics.RetrieveAPIView):

    lookup_field = 'uid'
    serializer_class = serializers.GetCollarAccountDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CollarAccount.objects.filter(organization=self.request.user.organization)


class GetCollarIndividualsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetCollarIndividualsSerializer

    def get_queryset(self):
        serializer = serializers.GetCollarIndividualsQueryParamsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        query_params = serializer.data
        user = self.request.user

        try:
            collar_account = CollarAccount.objects.get(is_active=True, organization=user.organization, uid=query_params['collar_account_uid'])
        except CollarAccount.DoesNotExist:
            return CollarIndividual.objects.none()

        return CollarIndividual.objects.filter(is_active=True, collar_account=collar_account)


class GetCollarIndividualDetailView(generics.RetrieveAPIView):

    lookup_field = 'uid'
    serializer_class = serializers.GetCollarIndividualDetailSerializer
    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CollarIndividual.objects.filter(collar_account__organization=self.request.user.organization)


class UpdateCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateCollarAccountSerializer

    def post(self, request):
        serializer = serializers.UpdateCollarAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        update_data = serializer.data
        collar_account_uid = update_data.pop('collar_account_uid')

        try:
            collar_account = CollarAccount.objects.get(uid=collar_account_uid)
        except CollarAccount.DoesNotExist:
            return Response({
                'error': 'collar_account_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if collar_account.organization != user.organization and not user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        CollarAccount.objects.filter(uid=collar_account.uid).update(datetime_updated=timezone.now(), **update_data)

        message = f'{collar_account.species} collar account updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


class UpdateCollarIndividualView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateCollarIndividualSerializer

    def post(self, request):
        serializer = serializers.UpdateCollarIndividualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        update_data = serializer.data
        collar_individual_uid = update_data.pop('collar_individual_uid')

        try:
            collar_individual = CollarIndividual.objects.get(uid=collar_individual_uid)
        except CollarIndividual.DoesNotExist:
            return Response({
                'error': 'collar_individual_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        if collar_individual.collar_account.organization != user.organization and not user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        CollarIndividual.objects.filter(uid=collar_individual.uid).update(datetime_updated=timezone.now(), **update_data)

        message = f'{collar_individual.collar_account.species} collar individual updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)














