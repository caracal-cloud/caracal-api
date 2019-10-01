
from django.conf import settings

from caracal.common import aws


def schedule_drives_get_data(drive_account, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_get_static_{drive_account.provider}_{drive_account.file_type}_data'
    lambda_function = aws.get_lambda_function(function_name)

    file_type = drive_account.file_type
    provider = drive_account.provider
    short_name = organization.short_name
    rule_name = get_drives_get_data_rule_name(short_name, provider, file_type, settings.STAGE, drive_account.uid)

    get_data_rule_input = {
        'account_uid': str(drive_account.uid)
    }

    aws.schedule_lambda_function(lambda_function['arn'], lambda_function['name'], get_data_rule_input,
                                 rule_name, settings.COLLARS_GET_DATA_RATE_MINUTES)

    return {
        'rule_name': rule_name
    }


def get_drives_get_data_rule_name(short_name, provider, file_type, stage, drive_account_uid):

    # white-willow-prod-drives-get-google-google_sheet-a8sl

    stage = stage[:4]
    provider = provider[:10]
    file_type = file_type[:10]
    drive_account_uid = str(drive_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-drives-get-{provider}-{file_type}-{drive_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name