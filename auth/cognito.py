import boto3
import botocore
from django.conf import settings
import os
from rest_framework.authentication import get_authorization_header
from warrant import Cognito


def confirm_forgot_password(email, confirmation_code, new_password, cognito_idp_client):
    params = {
        'ClientId': settings.COGNITO_APP_ID,
        'Username': email,
        'ConfirmationCode': confirmation_code,
        'Password': new_password
    }
    cognito_idp_client.confirm_forgot_password(**params)


def confirm_user(email):
    cognito_idp_client = get_cognito_idp_client()
    cognito_idp_client.admin_confirm_sign_up(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email
    )


def get_cognito_idp_client():
    kwargs = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        'region_name': settings.AWS_REGION
    }
    return boto3.client('cognito-idp', **kwargs)


def get_warrant_wrapper_client(email=None):
    return Cognito(user_pool_id=settings.COGNITO_USER_POOL_ID,
                   client_id=settings.COGNITO_APP_ID,
                   user_pool_region=settings.AWS_REGION,
                   access_key=settings.AWS_ACCESS_KEY_ID,
                   secret_key=settings.AWS_SECRET_ACCESS_KEY,
                   username=email)


def get_tokens(warrant_client, password):
    warrant_client.authenticate(password)
    return {
        'access_token': warrant_client.access_token,
        'refresh_token': warrant_client.refresh_token
    }


def register(email, password, cognito_idp_client):
    client = get_cognito_idp_client()
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


def sign_out_user(email):
    client = get_cognito_idp_client()
    client.admin_user_global_sign_out(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email
    )




