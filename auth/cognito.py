import boto3
import botocore
from django.conf import settings
import os
from rest_framework.authentication import get_authorization_header


def get_cognito_idp_client():
    kwargs = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        'region_name': settings.AWS_REGION
    }
    return boto3.client('cognito-idp', **kwargs)

def get_tokens(email, password, cognito_idp_client):

    response = cognito_idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': email,
            'PASSWORD': password
        },
        ClientId=settings.COGNITO_APP_ID
    )

    auth_result = response['AuthenticationResult']
    return {
        'access_token': auth_result['AccessToken'],
        'refresh_token': auth_result['RefreshToken']
    }


def register(email, password, cognito_idp_client):
    params = {
        'ClientId': settings.COGNITO_APP_ID,
        'Username': email,
        'Password': password,
        'UserAttributes': [{
            'Name': 'email',
            'Value': email
        }]
    }
    response = cognito_idp_client.sign_up(**params)
    return response.get('UserSub', None)


def confirm_user(email):
    cognito_idp_client = get_cognito_idp_client()
    cognito_idp_client.admin_confirm_sign_up(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email
    )


def remove_all_users():
    cognito_idp_client = get_cognito_idp_client()
    response = cognito_idp_client.list_users(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        AttributesToGet=[
            'email',
        ],
    )
    users = response['Users']
    print("...removing %d Cognito users" % (len(users)))
    for user in users:
        sub = user['Username']
        cognito_idp_client.admin_delete_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=sub
        )















