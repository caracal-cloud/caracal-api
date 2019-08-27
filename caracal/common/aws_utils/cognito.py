
from botocore.exceptions import ClientError, ParamValidationError
from django.conf import settings
import uuid

from caracal.common.aws_utils import get_boto_client
from caracal.common.aws_utils import exceptions


def change_password(old_password, new_password, access_token):

    client = get_boto_client('cognito-idp')

    try:
        client.change_password(
            PreviousPassword=old_password,
            ProposedPassword=new_password,
            AccessToken=access_token
        )
    except client.exceptions.NotAuthorizedException:
        raise exceptions.NotAuthorizedException
    except client.exceptions.LimitExceededException:
        raise exceptions.LimitExceededException
    except ParamValidationError:
        raise exceptions.ParamValidationError



def confirm_account(email):

    client = get_boto_client('cognito-idp')

    client.admin_confirm_sign_up(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email
    )


def create_user(email, password, registration_method="email"):

    # using this to add superusers as well, with registration "superuser", lambda checks this

    client = get_boto_client('cognito-idp')

    try:
        response = client.sign_up(
            ClientId=settings.COGNITO_APP_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                }
            ],
            ValidationData=[
                {
                    'Name': 'registration_method',
                    'Value': registration_method
                },
            ]
        )
    except ParamValidationError:
        raise exceptions.ParamValidationError
    except client.exceptions.InvalidParameterException:
        raise exceptions.InvalidParameterException
    except client.exceptions.UsernameExistsException:
        raise exceptions.UsernameExistsException
    else:
        sub = response['UserSub']
        return sub


def create_sub_user(email):

    client = get_boto_client('cognito-idp')

    temp_password = create_temp_password()

    try:
        response = client.admin_create_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                }
            ],
            TemporaryPassword=temp_password,
            DesiredDeliveryMediums=['EMAIL']
        )
    except client.exceptions.UsernameExistsException:
        raise exceptions.UsernameExistsException
    else:
        for attr in response['User']['Attributes']:
            if attr['Name'] == 'sub':
                return attr['Value']


def delete_all_users():
    assert settings.STAGE != 'production'

    client = get_boto_client('cognito-idp')
    response = client.list_users(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        AttributesToGet=[
            'email',
        ],
    )
    users = response['Users']
    print("...removing %d Cognito users" % (len(users)))
    for user in users:
        sub = user['Username']
        client.admin_delete_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=sub
        )


def delete_testing_users():
    # remove testing users that start with a digit
    client = get_boto_client('cognito-idp')
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
            if attr['Name'] == 'email' and attr['Value'][0].isdigit():
                print("...removing %s" % attr['Value'])
                sub = user['Username']
                client.admin_delete_user(UserPoolId=settings.COGNITO_USER_POOL_ID, Username=sub)
                break


def get_is_email_verified(email):

    client = get_boto_client('cognito-idp')
    cognito_response = client.admin_get_user(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email
    )

    is_email_verified = False
    for attr in cognito_response['UserAttributes']: # TODO: better way to loop through dictionary to compare a value?
        if attr['Name'] == 'email_verified':
            is_email_verified = attr['Value'] == 'true'

    return is_email_verified


def refresh_access_token(refresh_token):

    client = get_boto_client('cognito-idp')

    try:
        response = client.initiate_auth(
            ClientId=settings.COGNITO_APP_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token,
            }
        )
    except client.exceptions.NotAuthorizedException:
        raise exceptions.NotAuthorizedException

    return response['AuthenticationResult']['AccessToken'] # fixme: is this safe?


def reset_password_start(email):
    """
    Start the password reset flow - sends an email to the user
    """

    client = get_boto_client('cognito-idp')

    try:
        client.forgot_password(
            ClientId=settings.COGNITO_APP_ID,
            Username=email
        )
    except client.exceptions.NotAuthorizedException:
        raise exceptions.NotAuthorizedException
    except client.exceptions.InvalidParameterException:
        raise exceptions.InvalidParameterException
    except client.exceptions.LimitExceededException:
        raise exceptions.LimitExceededException
    except client.exceptions.UserNotFoundException:
        raise exceptions.UserNotFoundException


def reset_password_confirm(email, code, password):
    """
    Complete the password reset flow - use code and new password to change
    """

    client = get_boto_client('cognito-idp')

    try:
        client.confirm_forgot_password(
            ClientId=settings.COGNITO_APP_ID,
            Username=email,
            ConfirmationCode=code,
            Password=password
        )
    except client.exceptions.CodeMismatchException:
        raise exceptions.CodeMismatchException
    except client.exceptions.ExpiredCodeException:
        raise exceptions.ExpiredCodeException
    except client.exceptions.UserNotFoundException:
        raise exceptions.UserNotFoundException
    except ParamValidationError:
        raise exceptions.ParamValidationError


def reset_password_forced(email, old_password, new_password):
    """
    Change the user's password if user is in forced password change state
    """

    client = get_boto_client('cognito-idp')

    # try to authenticate and see if cognito responds with new password challenge
    try:
        response = client.admin_initiate_auth(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_APP_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': old_password
            }
        )
    except client.exceptions.NotAuthorizedException:
        raise exceptions.NotAuthorizedException
    except client.exceptions.UserNotConfirmedException:
        raise exceptions.UserNotConfirmedException
    except client.exceptions.UserNotFoundException:
        raise exceptions.UserNotFoundException

    # change password as admin - user has already proven they know old password
    if response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
        try:
            client.admin_set_user_password(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email,
                Password=new_password,
                Permanent=True
            )
        except ParamValidationError:
            raise exceptions.ParamValidationError


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

    client = get_boto_client('cognito-idp')
    client.admin_user_global_sign_out(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email
    )


def update_account(email, attrs):

    client = get_boto_client('cognito-idp')
    try:
        client.admin_update_user_attributes(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email,
            UserAttributes=attrs
        )
    except client.exceptions.AliasExistsException:
        raise exceptions.AliasExistsException


def verify_email(email):

    client = get_boto_client('cognito-idp')
    client.admin_update_user_attributes(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email,
        UserAttributes=[
            {
                'Name': 'email_verified',
                'Value': 'true'
            },
        ]
    )


def verify_user_attribute(attribute, code, access_token):

    client = get_boto_client('cognito-idp')

    try:
        client.verify_user_attribute(
            AccessToken=access_token,
            AttributeName=attribute,
            Code=code
        )
    except client.exceptions.CodeMismatchException:
        raise exceptions.CodeMismatchException


# Utils

def create_temp_password():
    pwd = str(uuid.uuid4()).split('-')[0]
    pwd = pwd.lower() # just to be sure
    return pwd