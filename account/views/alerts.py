
from datetime import datetime, timedelta, timezone
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from account import serializers
from account.models import Account, AlertRecipient
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication


class AddRecipientView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddRecipientSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        organization = user.organization

        data = serializer.validated_data

        recipient = AlertRecipient.objects.create(organization=organization, account=user, **data)

        contact = recipient.email if recipient.email is not None else recipient.phone_number
        message = f'Alert recipient {contact} added by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response({
            'recipient_uid': recipient.uid
        }, status=status.HTTP_201_CREATED)


class DeleteRecipientView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteRecipientSerializer

    def post(self, request):
        serializer = serializers.DeleteRecipientSerializer(data=request.data)
        serializer.is_valid(True)

        user = request.user
        organization = user.organization

        recipient_uid = serializer.data['recipient_uid']

        try:
            recipient = AlertRecipient.objects.get(uid=recipient_uid, organization=organization, is_active=True)
        except AlertRecipient.DoesNotExist:
            return Response({
                'error': 'recipient_does_not_exist',
                'message': 'recipient does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)

        recipient.is_active = False
        recipient.save()

        contact = recipient.email if recipient.email is not None else recipient.phone_number
        message = f'Alert recipient {contact} deleted by {user.name}'
        ActivityChange.objects.create(organization=user.organization, account=user, message=message)

        return Response(status=status.HTTP_200_OK)


class GetRecipientsView(generics.ListAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetRecipientsSerializer

    def get_queryset(self):
        organization = self.request.user.organization
        return AlertRecipient.objects.filter(organization=organization, is_active=True)



