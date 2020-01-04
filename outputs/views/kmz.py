
from django.conf import settings
import os
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response

from auth.backends import CognitoAuthentication
from caracal.common.aws_utils import dynamodb, s3


class GetKmzHrefsView(views.APIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        kmz_object_keys = s3.get_files(f'{user.organization.short_name}/kmz', '.kmz', settings.S3_USER_DATA_BUCKET)

        # [{'p': 'cd13ed3c', 'u': 'admin', 'permissions': ['all']}]
        # todo: returning all for now...
        credentials = dynamodb.get_dynamodb_credentials(user.organization.short_name)

        hrefs = dict()
        for object_key in kmz_object_keys:

            parts = os.path.split(object_key)[0].split('/')[2:]
            category = ' / '.join(parts)

            if len(parts) == 0:
                category = 'other'

            if category not in hrefs.keys():
                hrefs[category] = list()

            base_href = f'https://users.caracal.cloud/{object_key}'
            for creds in credentials:
                href = f'{base_href}?u={creds["u"]}&p={creds["p"]}'
                hrefs[category].append(href)

        return Response(data=hrefs, status=status.HTTP_200_OK)



