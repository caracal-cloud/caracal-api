
import boto3, botocore
from datetime import datetime
from django.conf import settings
import sentry_sdk
import traceback


import time

def send_email(subject, message, sender, recipients):

    kwargs = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        'region_name': settings.AWS_REGION
    }
    client = boto3.client('ses', **kwargs)

    message = {
        'Body': {
            'Text': {
                'Charset': 'UTF-8',
                'Data': message
            },
        },
        'Subject': {
            'Charset': 'UTF-8',
            'Data': subject
        }
    }
    destination = {
        'ToAddresses': recipients
    }

    try:
        client.send_email(
            Source=sender,
            Destination=destination,
            Message=message)
    except:
        sentry_sdk.capture_exception()
        return False

    return True
