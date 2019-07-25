
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from account import serializers


class RegisterView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RegisterSerializer

    @swagger_auto_schema(responses={
        status.HTTP_201_CREATED: '',
        status.HTTP_400_BAD_REQUEST: 'email_already_exists, invalid_organization_short_name, '
                                     'organization_short_name_already_exists',
    }, security=[], operation_id='account - register')
    def post(self, request):

        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = serializer.save()
        if isinstance(response, Response):
            return response
        else:
            return Response(status=status.HTTP_201_CREATED)

