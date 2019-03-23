from django.conf import settings

from rest_framework import permissions, status, generics
from rest_framework.response import Response
import traceback

from collars import serializers


class AddCollarView(generics.GenericAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = serializers.AddCollarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)









