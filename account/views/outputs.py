
from django.conf import settings
from rest_framework import permissions, status, views
from rest_framework.response import Response
import uuid

from account import serializers
from auth.backends import CognitoAuthentication
from caracal.common import aws


class GetKmzHrefsView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # TODO: get all kmz files from s3 for this organization...
        kmz_object_keys = aws.get_s3_files('.kmz', user.organization.short_name, settings.S3_USER_DATA_TABLE)

        # [{'p': 'cd13ed3c', 'u': 'admin', 'permissions': ['all']}]
        credentials = aws.get_dynamo_credentials(user.organization.short_name)

        hrefs = list()
        for kmz in kmz_object_keys:
            base_href = f'https://data.caracal.cloud/{kmz}'
            for creds in credentials:
                href = f'{base_href}?u={creds["u"]}&p={creds["p"]}'
                hrefs.append(href)

        return Response(status=status.HTTP_200_OK, data={
            'count': len(hrefs),
            'next': None,
            'previous': None,
            'results': hrefs
        })



