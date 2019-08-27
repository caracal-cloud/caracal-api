
import boto3
from django.conf import settings


def get_boto_client(service):

    params = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        'region_name': settings.AWS_REGION
    }

    return boto3.client(service, **params)
