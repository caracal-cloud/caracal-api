
from django.conf import settings

from caracal.common.aws_utils import _lambda


def schedule_collars_get_data(data, collar_account, organization):

    species = data['type']
    provider = data['provider']

    get_data_rule_input = dict()
    get_data_rule_input['account_uid'] = str(collar_account.uid)

    if provider == 'orbcomm':
        get_data_rule_input['orbcomm_timezone'] = 2 # fixme: send offset integer data['orbcomm_timezone']
        get_data_rule_input['orbcomm_company_id'] = data['orbcomm_company_id']

    elif provider == 'savannah_tracking':
        get_data_rule_input['savannah_tracking_username'] = data['savannah_tracking_username']
        get_data_rule_input['savannah_tracking_password'] = data['savannah_tracking_password']

    else:
        return {
            'error': 'unknown_provider'
        }

    function_name = f'caracal_{settings.STAGE.lower()}_get_realtime_{provider}_data'
    lambda_function = _lambda.get_lambda_function(function_name)

    short_name = organization.short_name
    rule_name = get_collars_get_data_rule_name(short_name, settings.STAGE, provider, species, collar_account.uid)

    _lambda.schedule_lambda_function(lambda_function['arn'], lambda_function['name'], get_data_rule_input,
                                 rule_name, settings.COLLARS_GET_DATA_RATE_MINUTES)

    return {
        'rule_name': rule_name
    }


def get_collars_get_data_rule_name(short_name, stage, provider, species, collar_account_uid):

    stage = stage[:4]
    species = species[:10]
    collar_account_uid = str(collar_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-cllrs-get-{provider}-{species}-{collar_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


