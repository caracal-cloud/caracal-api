
from datetime import datetime, timedelta, timezone
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from account import serializers
from account.models import Account
from activity.models import ActivityChange
from auth.backends import CognitoAuthentication


class AddRecipientView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddRecipientSerializer

    def post(self, request):
        return Response(status=status.HTTP_201_CREATED)



class DeleteRecipientView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.DeleteRecipientSerializer

    def post(self, request):
        return Response(status=status.HTTP_200_OK)


class GetRecipientsView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.GetRecipientsSerializer

    def post(self, request):
        return Response(status=status.HTTP_200_OK)