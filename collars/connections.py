
from django.conf import settings

from caracal.common import aws
from outputs.models import AgolAccount, DataConnection


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


def get_collars_get_data_rule_name(short_name, stage, provider, species, collar_account_uid):

    stage = stage[:4]
    species = species[:10]
    collar_account_uid = str(collar_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-cllrs-get-{provider}-{species}-{collar_account_uid}'
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
        schedule_collars_agol(species, realtime_account, connection, organization)

    if data.get('output_kml', False):
        schedule_collars_kml(species, realtime_account, organization)


# Update KML

def delete_collars_kml(realtime_account):

    if realtime_account.cloudwatch_update_kml_rule_names:
        update_kml_rule_names = realtime_account.cloudwatch_update_kml_rule_names.split(',')
        for rule_name in update_kml_rule_names:
            aws.delete_cloudwatch_rule(rule_name)

    realtime_account.cloudwatch_update_kml_rule_names = None
    realtime_account.save()


def schedule_collars_kml(species, realtime_account, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_realtime_kml'
    update_kml_function = aws.get_lambda_function(function_name)

    rule_names = list()
    for period in settings.KML_PERIOD_HOURS:

        rate_minutes = int(period / 2.5) # longer for larger periods

        update_kml_input = {
            'rt_account_uid': str(realtime_account.uid),
            'period_hours': period
        }

        short_name = organization.short_name
        rule_name = get_collars_update_kml_rule_name(short_name, realtime_account.uid, settings.STAGE, species, period)
        rule_names.append(rule_name)

        aws.schedule_lambda_function(update_kml_function['arn'], update_kml_function['name'], update_kml_input,
                                     rule_name, rate_minutes)

    realtime_account.cloudwatch_update_kml_rule_names = ','.join(rule_names)
    realtime_account.save()


def get_collars_update_kml_rule_name(short_name, collar_account_uid, stage, species, period):

    stage = stage[:4]
    species = species[:10]
    collar_account_uid = str(collar_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-cllrs-kml-{species}-{period}-{collar_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


# Update ArcGIS Online

def delete_collars_agol(agol_account=None, realtime_account=None, connection=None):
    # can be called with a connection, or accounts for connection lookup

    if connection is None:
        try:
            connection = DataConnection.objects.get(realtime_account=realtime_account, agol_account=agol_account)
        except DataConnection.DoesNotExist:
            print('connection does not exist, no problem')
            return

    aws.delete_cloudwatch_rule(connection.cloudwatch_update_rule_name)
    connection.delete()


def schedule_collars_agol(species, realtime_account, connection, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_realtime_agol'
    update_agol_function = aws.get_lambda_function(function_name)

    update_agol_input = {
        'connection_uid': str(connection.uid),
    }

    short_name = organization.short_name
    rule_name = get_collars_update_agol_rule_name(short_name, realtime_account.uid, settings.STAGE, species)

    aws.schedule_lambda_function(update_agol_function['arn'], update_agol_function['name'], update_agol_input,
                                 rule_name, settings.AGOL_UPDATE_RATE_MINUTES)

    connection.cloudwatch_update_rule_name = rule_name
    connection.save()


def get_collars_update_agol_rule_name(short_name, collar_account_uid, stage, species):

    stage = stage[:4]
    species = species[:10]
    collar_account_uid = str(collar_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-cllrs-agol-{species}-{collar_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


def update_collars_outputs(data, realtime_account, user):

    # output flag exists
    output_kml = data.get('output_kml')
    if output_kml is not None:

        # output flag is different than current state (kml rule names is alias for kml output enabled)
        if output_kml != (realtime_account.cloudwatch_update_kml_rule_names is not None):

            if output_kml:
                schedule_collars_kml(realtime_account.type, realtime_account, user.organization)

            else:
                delete_collars_kml(realtime_account)

    # user.agol_account will not be None, validated before
    output_agol = data.get('output_agol')
    if output_agol is not None:

        try:
            connection = DataConnection.objects.get(realtime_account=realtime_account, agol_account=user.agol_account)
        except DataConnection.DoesNotExist:
            connection = None

        # output flag is different than current state (agol connection for account is alias for agol output enabled)
        if output_agol != (connection is not None):

            if output_agol:
                # create a connection and schedule update
                connection = DataConnection.objects.create(organization=user.organization, account=user,
                                                           realtime_account=realtime_account, agol_account=user.agol_account)
                schedule_collars_agol(realtime_account.type, realtime_account, connection, user.organization)

            else:
                delete_collars_agol(connection=connection)

