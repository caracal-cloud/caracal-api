
import json

from caracal.common.aws_utils import get_boto_client


def get_lambda_function(function_name):

    client = get_boto_client('lambda')

    fn_response = client.get_function(FunctionName=function_name)

    return {
        'arn': fn_response['Configuration']['FunctionArn'],
        'name': fn_response['Configuration']['FunctionName']
    }


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


