
from django.conf import settings
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import uuid

from account import serializers
from auth.backends import CognitoAuthentication
from caracal.common import aws


class AgolOauthView(views.APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK)



class GoogleOauthView(views.APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK)