from django.conf import settings
import os
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from auth.backends import CognitoAuthentication
from caracal.common.aws_utils import dynamodb, s3



class GetAccounts(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response([], status=status.HTTP_200_OK)


