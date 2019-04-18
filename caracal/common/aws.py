

import boto3
import json


def get_lambda_function(function_name):
    lambda_client = boto3.client('lambda')
    fn_response = lambda_client.get_function(FunctionName=function_name)
    return {
        'arn': fn_response['Configuration']['FunctionArn'],
        'name': fn_response['Configuration']['FunctionName']
    }


def schedule_lambda_function(fn_arn, fn_name, rule_input, rule_name):
    events_client = boto3.client('events')
    lambda_client = boto3.client('lambda')

    # 1. Create rule
    rule_response = events_client.put_rule(
        Name=rule_name,
        ScheduleExpression='rate(7 minutes)',  # TODO: use global configuration
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