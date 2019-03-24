from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from rest_framework import permissions, status, generics
from rest_framework.response import Response
import sentry_sdk
import traceback

from auth.backends import CognitoAuthentication
from collars import serializers
from collars.models import CollarAccount, CollarIndividual, CollarPosition, CollarProvider


class AddCollarAccountView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = serializers.AddCollarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        provider_short_name = data.pop('provider_short_name')

        try:
            provider = CollarProvider.objects.get(short_name=provider_short_name, is_available=True)
        except CollarProvider.DoesNotExist:
            return Response({
                'error': 'unknown_provider'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            account = CollarAccount(organization=request.user.organization, provider=provider, **data)
            account.save()
        except ValidationError:
            return Response({
                'error': 'account_already_added'
            }, status=status.HTTP_400_BAD_REQUEST)

        # TODO: add user activity event (i.e. user1 added elephant collar account)
        return Response({
            'collar_account_uid': account.uid
        }, status=status.HTTP_201_CREATED)


class AddCollarIndividualView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = serializers.AddCollarIndividualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collar_account_uid = serializer.data['collar_account_uid']
        collar_id = serializer.data['collar_id']

        # collar account belongs to user's organization
        try:
            collar_account = CollarAccount.objects.get(uid=collar_account_uid)
        except CollarAccount.DoesNotExist:
            return Response({
                'error': 'collar_account_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        # not same organization and not superuser (Lambda)
        if collar_account.organization != request.user.organization and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            individual = CollarIndividual.objects.create(collar_account=collar_account, collar_id=collar_id)
        except IntegrityError:
            return Response({
                'error': 'collar_individual_already_exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'collar_individual_uid': individual.uid,
        }, status=status.HTTP_201_CREATED)


class AddCollarIndividualPositionView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = serializers.AddCollarIndividualPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collar_account_uid = serializer.data['collar_account_uid']
        collar_id = serializer.data['collar_id']
        datetime_recorded = serializer.data['datetime_recorded']
        latitude = float(serializer.data['latitude']) # todo: check if this is safe
        longitude = float(serializer.data['longitude'])

        try:
            collar_account = CollarAccount.objects.get(uid=collar_account_uid)
        except CollarAccount.DoesNotExist:
            return Response({
                'error': 'collar_account_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            individual = CollarIndividual.objects.get(collar_account=collar_account, collar_id=collar_id)
        except CollarIndividual.DoesNotExist:
            return Response({
                'error': 'collar_individual_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        # not same organization and not superuser (Lambda)
        if collar_account.organization != request.user.organization and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            point = Point(x=longitude, y=latitude, srid=settings.SRID)
            CollarPosition.objects.create(datetime_recorded=datetime_recorded,
                                          individual=individual,
                                          position=point)
            return Response(status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({
                'error': 'collar_position_already_exists'
            }, status=status.HTTP_400_BAD_REQUEST)


class UpdateCollarIndividualView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = serializers.UpdateCollarIndividualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_data = serializer.data
        collar_account_uid = update_data.pop('collar_account_uid')
        collar_id = update_data.pop('collar_id')

        try:
            collar_account = CollarAccount.objects.get(uid=collar_account_uid)
        except CollarAccount.DoesNotExist:
            return Response({
                'error': 'collar_account_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            CollarIndividual.objects.get(collar_account=collar_account, collar_id=collar_id)
        except CollarIndividual.DoesNotExist:
            return Response({
                'error': 'collar_individual_does_not_exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        # not same organization and not superuser (Lambda)
        if collar_account.organization != request.user.organization and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        CollarIndividual.objects.filter(collar_account=collar_account, collar_id=collar_id).update(**update_data)

        return Response(status=status.HTTP_200_OK)














