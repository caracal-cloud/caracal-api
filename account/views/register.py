
from django.conf import settings
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from account import serializers



class RegisterView(generics.GenericAPIView):

    def post(self, request):
        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = serializer.save()
        if isinstance(response, Response):
            return response
        else:
            return Response(status=status.HTTP_201_CREATED)

