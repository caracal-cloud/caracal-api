
from django.conf import settings

from caracal.common import aws
from outputs.models import DataConnection


# Get data

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
    lambda_function = aws.get_lambda_function(function_name)

    short_name = organization.short_name
    rule_name = get_collars_get_data_rule_name(short_name, settings.STAGE, provider, species, collar_account.uid)

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


# Outputs

def schedule_collars_outputs(data, realtime_account, user, agol_account=None):

    species = data['type']
    organization = user.organization

    if data.get('output_agol', False) and agol_account is not None:
        # create a connection and schedule update
        connection = DataConnection.objects.create(organization=organization, account=user,
                                                   realtime_account=realtime_account, agol_account=agol_account)
        schedule_collars_agol(species, connection, organization)

    if data.get('output_kml', False):
        schedule_collars_kml(species, realtime_account, organization)


# Update KML

def schedule_collars_kml(species, realtime_account, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_realtime_kml'
    update_kml_function = aws.get_lambda_function(function_name)

    rule_names = []
    for period in settings.COLLARS_KML_PERIOD_HOURS:

        rate_minutes = int(period / 2.5) # longer for larger periods

        update_kml_input = {
            'rt_account_uid': str(realtime_account.uid),
            'period_hours': period
        }

        short_name = organization.short_name
        rule_name = get_collars_update_kml_rule_name(short_name, settings.STAGE, species, period)
        rule_names.append(rule_name)

        aws.schedule_lambda_function(update_kml_function['arn'], update_kml_function['name'], update_kml_input,
                                     rule_name, rate_minutes)

    # append to cloudwatch_update_kml_rule_names
    realtime_account.cloudwatch_update_kml_rule_names = ','.join(rule_names)
    realtime_account.save()


def get_collars_update_kml_rule_name(org_short_name, stage, species, period):

    stage = stage[:4]
    species = species[:10]

    rule_name = f'{org_short_name}-{stage}-cllrs-kml-{species}-{period}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


# Update ArcGIS Online

def schedule_collars_agol(species, connection, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_realtime_agol'
    update_agol_function = aws.get_lambda_function(function_name)

    update_agol_input = {
        'connection_uid': str(connection.uid),
    }

    short_name = organization.short_name
    rule_name = get_collars_update_agol_rule_name(short_name, settings.STAGE, species)

    aws.schedule_lambda_function(update_agol_function['arn'], update_agol_function['name'], update_agol_input,
                                 rule_name, settings.AGOL_UPDATE_RATE_MINUTES)

    connection.cloudwatch_update_rule_name = rule_name
    connection.save()


def get_collars_update_agol_rule_name(org_short_name, stage, species):

    stage = stage[:4]
    species = species[:10]

    rule_name = f'{org_short_name}-{stage}-cllrs-agol-{species}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name



