
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import uuid

from account import serializers
from account.models import Account
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication


class GetProfileView(generics.RetrieveAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetProfileSerializer

    def get_object(self):
        return self.request.user


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
        serializer = serializers.UpdateAccountSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_200_OK)


class UpdateOrganizationView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateOrganizationSerializer

    @swagger_auto_schema(responses={
        status.HTTP_200_OK: '',
        status.HTTP_400_BAD_REQUEST: '',
    }, security=[settings.SWAGGER_SETTINGS['SECURITY_DEFINITIONS']], operation_id='account - update organization')
    def post(self, request):
        user = request.user
        serializer = serializers.UpdateOrganizationSerializer(user.organization, data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.is_admin:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer.save(organization=user.organization)

        message = f'organization profile updated by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)



