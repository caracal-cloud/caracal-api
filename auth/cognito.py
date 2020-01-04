import boto3
import botocore
from django.conf import settings
import os
from rest_framework.authentication import get_authorization_header

from caracal.common.aws_utils import exceptions, get_boto_client


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


# TODO: refactor this to use exceptions like ql
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


def remove_testing_users():
    assert settings.TESTING

    # remove testing users that start with a digit
    client = get_cognito_idp_client()
    response = client.list_users(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        AttributesToGet=[
            'email',
        ],
    )
    users = response['Users']
    print("...retrieving %d Cognito users" % (len(users)))
    for user in users:
        for attr in user['Attributes']:
            if attr['Name'] == 'email' and attr['Value'][0].isdigit(): # if it starts with a digit
                print("...removing %s" % attr['Value'])
                sub = user['Username']
                client.admin_delete_user(UserPoolId=settings.COGNITO_USER_POOL_ID, Username=sub)
                break


def sign_in_user(email, password):

    client = get_boto_client('cognito-idp')

    try:
        response = client.admin_initiate_auth(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_APP_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH', # must configure app client
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
    except client.exceptions.NotAuthorizedException:
        raise exceptions.NotAuthorizedException
    except client.exceptions.UserNotConfirmedException:
        raise exceptions.UserNotConfirmedException
    except client.exceptions.UserNotFoundException:
        raise exceptions.UserNotFoundException

    # check if password change required
    if response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
        raise exceptions.NewPasswordRequiredError

    return {
        'access_token': response['AuthenticationResult']['AccessToken'],
        'refresh_token': response['AuthenticationResult']['RefreshToken'],
        'id_token': response['AuthenticationResult']['IdToken']
    }


def sign_out_user(email):
    client = get_cognito_idp_client()
    client.admin_user_global_sign_out(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email
    )




