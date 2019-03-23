from django.conf import settings
from django.core.exceptions import ValidationError

from rest_framework import permissions, status, generics
from rest_framework.response import Response
import traceback

from auth.backends import CognitoAuthentication
from collars import serializers
from collars.models import CollarAccount


class AddCollarView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = serializers.AddCollarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = CollarAccount.objects.create(organization=request.user.organization, **serializer.data)
        except ValidationError:
            return Response({
                'error': 'account_already_added'
            }, status=status.HTTP_400_BAD_REQUEST)

        # TODO: add user activity event (i.e. user1 added elephant collar account)
        return Response(status=status.HTTP_201_CREATED)

