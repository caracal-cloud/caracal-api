
from caracal.common import aws
from django.conf import settings
from outputs.models import DataConnection


def schedule_realtime_outputs(data, type, source, realtime_account, user, agol_account=None):

    organization = user.organization

    if data.get('output_agol', False) and agol_account is not None:
        # create a connection and schedule update
        connection = DataConnection.objects.create(organization=organization, account=user,
                                                   realtime_account=realtime_account, agol_account=agol_account)
        schedule_realtime_agol(type, source, realtime_account, connection, organization)

    if data.get('output_kml', False):
        schedule_realtime_kml(type, source, realtime_account, organization)


# ArcGIS Online

# TODO: make one agol delete function for all inputs (realtime, drive, custom_source)
def delete_realtime_agol(agol_account=None, realtime_account=None, connection=None):
    # can be called with a connection, or accounts for connection lookup
    if connection is None:
        try:
            connection = DataConnection.objects.get(realtime_account=realtime_account, agol_account=agol_account)
        except DataConnection.DoesNotExist:
            print('connection does not exist, no problem')
            return

    aws.delete_cloudwatch_rule(connection.cloudwatch_update_rule_name)
    connection.delete()


def schedule_realtime_agol(type, source, realtime_account, connection, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_realtime_agol'
    update_agol_function = aws.get_lambda_function(function_name)

    update_agol_input = {
        'connection_uid': str(connection.uid),
    }

    short_name = organization.short_name
    rule_name = get_realtime_update_agol_rule_name(short_name, realtime_account.uid, settings.STAGE, type, source)

    aws.schedule_lambda_function(update_agol_function['arn'], update_agol_function['name'], update_agol_input,
                                 rule_name, settings.AGOL_UPDATE_RATE_MINUTES)

    connection.cloudwatch_update_rule_name = rule_name
    connection.save()


def get_realtime_update_agol_rule_name(short_name, realtime_account_uid, stage, type, source):

    stage = stage[:4]
    type = type[:5]
    source = source[:5]
    realtime_account_uid = str(realtime_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-realtime-agol-{source}-{type}-{realtime_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


# KML

# TODO: one function for all inputs (realtime, drive, custom_source)
# TODO: make abstract model for inputs with cloudwatch_update_kml_rule_names and stuff...
def delete_realtime_kml(realtime_account):

    if realtime_account.cloudwatch_update_kml_rule_names:
        update_kml_rule_names = realtime_account.cloudwatch_update_kml_rule_names.split(',')
        for rule_name in update_kml_rule_names:
            aws.delete_cloudwatch_rule(rule_name)

    realtime_account.cloudwatch_update_kml_rule_names = None
    realtime_account.save()


def schedule_realtime_kml(type, source, realtime_account, organization):

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
        rule_name = get_realtime_update_kml_rule_name(short_name, realtime_account.uid, settings.STAGE, type, source, period)
        rule_names.append(rule_name)

        aws.schedule_lambda_function(update_kml_function['arn'], update_kml_function['name'], update_kml_input,
                                     rule_name, rate_minutes)

    realtime_account.cloudwatch_update_kml_rule_names = ','.join(rule_names)
    realtime_account.save()

def get_realtime_update_kml_rule_name(short_name, realtime_account_uid, stage, type, source, period):

    stage = stage[:4]
    type = type[:5]
    source = source[:5]
    realtime_account_uid = str(realtime_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-realtime-kml-{source}-{type}-{period}-{realtime_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


def update_realtime_outputs(data, realtime_account, user):

    # output flag exists
    output_kml = data.get('output_kml')
    if output_kml is not None:

        # output flag is different than current state (kml rule names is alias for kml output enabled)
        if output_kml != (realtime_account.cloudwatch_update_kml_rule_names is not None):

            if output_kml:
                schedule_realtime_kml(realtime_account.type, realtime_account.source, realtime_account, user.organization)

            else:
                delete_realtime_kml(realtime_account)

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
                schedule_realtime_agol(realtime_account.type, realtime_account.source, realtime_account, connection, user.organization)

            else:
                delete_realtime_agol(connection=connection)
