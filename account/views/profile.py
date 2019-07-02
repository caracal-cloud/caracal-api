
from django.conf import settings
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import uuid

from account import serializers
from account.models import Account
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication
from caracal.common import aws


class HelloCors(views.APIView):

    def get(self, request):
        return Response({
            'message': 'hello cors'
        }, status=status.HTTP_200_OK)


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



