
from django.conf import settings

from caracal.common import aws


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

    print('get_data_rule_input', get_data_rule_input)

    function_name = f'caracal_{settings.STAGE.lower()}_get_realtime_{provider}_data'

    print('function_name', function_name)

    lambda_function = aws.get_lambda_function(function_name)

    short_name = organization.short_name
    rule_name = get_collars_get_data_rule_name(short_name, settings.STAGE, provider, species, collar_account.uid)

    print('rule_name', rule_name)

    aws.schedule_lambda_function(lambda_function['arn'], lambda_function['name'], get_data_rule_input,
                                 rule_name, settings.COLLARS_GET_DATA_RATE_MINUTES)

    return {
        'rule_name': rule_name
    }


def get_collars_get_data_rule_name(org_short_name, stage, provider, species, collar_account_uid):

    stage = stage[:4]
    species = species[:10]
    collar_account_uid = str(collar_account_uid).split('-')[0][:4]

    rule_name = f'{org_short_name}-{stage}-cllrs-get-{provider}-{species}-{collar_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


def schedule_collars_outputs(data, organization):

    species = data['type']

    if data.get('output_agol', False):
        schedule_collars_agol()

    if data.get('output_kml', False):
        schedule_collars_kml(species, organization)


def schedule_collars_kml(species, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_create_collars_kml'
    create_kml_function = aws.get_lambda_function(function_name)

    for period in settings.COLLARS_KML_PERIOD_HOURS:

        rate_minutes = int(period / 2.5) # longer for larger periods

        create_kml_input = {
            'organization_uid': str(organization.uid),
            'species': species,
            'period_hours': period
        }

        print(rate_minutes)
        print(create_kml_input)

        short_name = organization.short_name
        rule_name = get_collars_create_kml_rule_name(short_name, settings.STAGE, species, period)

        aws.schedule_lambda_function(create_kml_function['arn'], create_kml_function['name'], create_kml_input,
                                     rule_name, rate_minutes)


def get_collars_create_kml_rule_name(org_short_name, stage, species, period):

    stage = stage[:4]
    species = species[:10]

    rule_name = f'{org_short_name}-{stage}-cllrs-kml-{species}-{period}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


def schedule_collars_agol():
    pass