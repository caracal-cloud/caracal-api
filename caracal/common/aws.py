
import boto3
from django.conf import settings
import json
from sentry_sdk import capture_message


def get_boto_client(service):
    params = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        'region_name': settings.AWS_REGION
    }
    return boto3.client(service, **params)


def get_global_config():

    client = get_boto_client('dynamodb')
    data = client.scan(
        TableName=settings.DYNAMO_CONFIG_TABLE_NAME,
    )

    config = dict()
    for item in data['Items']:
        name = item['name']['S']
        value = item['value']
        if 'S' in value.keys():
            config[name] = value['S']
        elif 'N' in value.keys():
            config[name] = int(value['N'])
        elif 'BOOL' in value.keys():
            config[name] = bool(value['BOOL'])
        elif 'L' in value.keys():
            config[name] = list()
            for v in value['L']:
                if 'N' in v.keys():
                    config[name].append(int(v['N']))
                elif 'S' in v.keys():
                    config[name].append(v['S'])
                else:
                    capture_message("Unsupported DynamoDB list element type: " + str(value), level='warning')
        else:
            capture_message("Unsupported DynamoDB type: " + str(value), level='warning')

    return config


def get_lambda_function(function_name):
    lambda_client = boto3.client('lambda')
    fn_response = lambda_client.get_function(FunctionName=function_name)
    return {
        'arn': fn_response['Configuration']['FunctionArn'],
        'name': fn_response['Configuration']['FunctionName']
    }


def schedule_lambda_function(fn_arn, fn_name, rule_input, rule_name, rate_minutes):
    events_client = boto3.client('events')
    lambda_client = boto3.client('lambda')

    # 1. Create rule
    rule_response = events_client.put_rule(
        Name=rule_name,
        ScheduleExpression='rate(%d minutes)' % rate_minutes,
        State='ENABLED',
    )

    # 2. Allow rule to trigger Lambda function
    lambda_client.add_permission(
        FunctionName=fn_name,
        StatementId=rule_name + '-event',
        Action='lambda:InvokeFunction',
        Principal='events.amazonaws.com',
        SourceArn=rule_response['RuleArn'],
    )

    # 3. Map rule to Lambda function
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': "1",
                'Arn': fn_arn,
                'Input': json.dumps(rule_input)
            },
        ]
    )