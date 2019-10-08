
import base64
import boto3
from django.conf import settings
from dynamodb_json import json_util as dynamodb_json_util
import json
from sentry_sdk import capture_message


def create_dynamo_credentials(org_short_name, username, password, permissions):
    assert isinstance(permissions, list)

    client = get_boto_client('dynamodb')
    item = {
        'organization': org_short_name,
        'credentials': [
            {
                'p': password,
                'u': username,
                'permissions': permissions
            }
        ]
    }

    dynamodb_json = dynamodb_json_util.dumps(item)
    dynamodb_json = json.loads(dynamodb_json)

    client.put_item(
        TableName=settings.S3_USER_CREDENTIALS_TABLE,
        Item=dynamodb_json
    )

def create_cognito_user(email, name, password, registration_method='email'):

    client = get_boto_client('cognito-idp')
    response = client.sign_up(
        ClientId=settings.COGNITO_APP_ID,
        #SecretHash=None,
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
        ],
    )

    sub = response['UserSub']
    return sub


def delete_cloudwatch_rule(rule_name):

    if rule_name is None:
        return

    client = get_boto_client('events')
    client.remove_targets(Rule=rule_name, Ids=["1"])
    client.delete_rule(Name=rule_name)


def get_boto_client(service):
    params = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        'region_name': settings.AWS_REGION
    }
    return boto3.client(service, **params)



# from caracal.common.aws import get_dynamo_credentials as get_creds
def get_dynamo_credentials(short_name):
    client = get_boto_client('dynamodb')
    item = client.get_item(
        TableName=settings.S3_USER_CREDENTIALS_TABLE,
        Key={
            'organization': {
                'S': short_name
            }
        }
    )

    item = dynamodb_json_util.loads(item)['Item']
    return item['credentials']


def get_global_config():

    client = get_boto_client('dynamodb')
    data = client.scan(
        TableName=settings.DYNAMO_CONFIG_TABLE_NAME,
    )

    items = dynamodb_json_util.loads(data['Items'])
    config = {item['name']: item['value'] for item in items}
    return config


def get_s3_files(prefix, suffix, bucket_name):

    # from caracal.common.aws import get_s3_files
    # get_s3_files('.kmz', 'garamba', 'caracal-user-data')

    s3_client = get_boto_client('s3')
    response = s3_client.list_objects(
        Bucket=bucket_name,
        EncodingType='url',
        Prefix=prefix
    )

    is_truncated = response['IsTruncated']
    next_marker = response.get('NextMarker') # if is_truncated, use next_marker
    contents = response.get('Contents', None)
    if contents is not None:
        objects = [c['Key'] for c in contents if c['Key'].endswith(suffix)]
        return objects
    else:
        return []


def get_lambda_function(function_name):

    client = get_boto_client('lambda')
    fn_response = client.get_function(FunctionName=function_name)
    return {
        'arn': fn_response['Configuration']['FunctionArn'],
        'name': fn_response['Configuration']['FunctionName']
    }


def get_presigned_url(object_key, bucket, expiration_secs):
    client = get_boto_client('s3')
    url = client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': object_key}, ExpiresIn=expiration_secs)
    return url


def put_firehose_record(payload, stream_name):

    # newline is the record deliminator so remove it from inside the record
    data = json.dumps(payload).replace('\n', '')

    client = get_boto_client('firehose')
    client.put_record(
        DeliveryStreamName=stream_name,
        Record={
            'Data': data + '\n'
        }
    )


def put_s3_item(body, bucket, object_key):
    client = get_boto_client('s3')
    client.put_object(Body=body, Bucket=bucket, Key=object_key)


def schedule_lambda_function(fn_arn, fn_name, rule_input, rule_name, rate_minutes):

    events_client = get_boto_client('events')
    lambda_client = get_boto_client('lambda')

    # 1. Create/update rule
    rule_response = events_client.put_rule(
        Name=rule_name,
        ScheduleExpression='rate(%d minutes)' % rate_minutes,
        State='ENABLED',
    )

    # use wildcard rule and default statement so policy size is not exceeded
    rule_parts = rule_response['RuleArn'].split('rule/')
    source_arn = f'{rule_parts[0]}rule/*'
    statement_id = f'{fn_name}-event'

    # 2. Allow rule to trigger Lambda function
    try:
        lambda_client.add_permission(
            FunctionName=fn_name,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=source_arn
        )
    except lambda_client.exceptions.ResourceConflictException:
        print("permission already exists")

    # 3. Map rule to Lambda function - need to call this even if permission already added
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': "1", # make sure always one, used when deleting rule
                'Arn': fn_arn,
                'Input': json.dumps(rule_input)
            },
        ]
    )