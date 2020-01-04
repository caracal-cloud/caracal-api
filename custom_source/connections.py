
from django.conf import settings
from caracal.common import agol
from caracal.common.aws_utils import cloudwatch, _lambda
from outputs.models import AgolAccount, DataConnection


def schedule_source_outputs(data, source, user, agol_account=None):

    organization = user.organization

    if data.get('output_agol', False) and agol_account is not None:
        # create a connection and schedule update
        connection = DataConnection.objects.create(organization=organization, account=user,
                                                   custom_source=source, agol_account=agol_account)
        schedule_source_agol(source, connection, organization)

        # create an ArcGIS Layer and update the connection object
        agol.verify_access_token_valid(agol_account)
        layer_id = agol.create_custom_source_layer(source.name, source.description, agol_account.feature_service_url,
                                              agol_account.oauth_access_token)
        connection.agol_layer_id = layer_id
        connection.save()

    if data.get('output_kml', False):
        schedule_source_kml(source, organization)

# KML

def delete_source_kml(source):

    if source.cloudwatch_update_kml_rule_names:
        update_kml_rule_names = source.cloudwatch_update_kml_rule_names.split(',')
        for rule_name in update_kml_rule_names:
            cloudwatch.delete_cloudwatch_rule(rule_name)

    source.cloudwatch_update_kml_rule_names = None
    source.save()


def schedule_source_kml(source, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_custom_source_kml'
    update_kml_function = _lambda.get_lambda_function(function_name)

    rule_names = list()
    for period in settings.KML_PERIOD_HOURS:

        rate_minutes = int(period / 2.5)

        update_kml_input = {
            'source_uid': str(source.uid),
            'period_hours': period
        }

        short_name = organization.short_name
        rule_name = get_source_update_kml_rule_name(short_name, source.uid, settings.STAGE, period)
        rule_names.append(rule_name)

        _lambda.schedule_lambda_function(update_kml_function['arn'], update_kml_function['name'], update_kml_input,
                                     rule_name, rate_minutes)

    source.cloudwatch_update_kml_rule_names = ','.join(rule_names)
    source.save()


def get_source_update_kml_rule_name(short_name, source_uid, stage, period):

    stage = stage[:4]
    source_uid = str(source_uid).split('-')[0][:8]

    rule_name = f'{short_name}-{stage}-source-kml-{period}-{source_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


# ArcGIS Online

def delete_source_agol(agol_account=None, source=None, connection=None):

    if connection is None:
        try:
            connection = DataConnection.objects.get(custom_source=source, agol_account=agol_account)
        except DataConnection.DoesNotExist:
            print('connection does not exist, no problem')
            return

    agol_account = connection.agol_account

    # update layer name...
    agol.verify_access_token_valid(agol_account)
    layer = agol.get_layer(connection.agol_layer_id, agol_account.feature_service_url, agol_account.oauth_access_token)
    agol.update_disconnected_layer_name(layer, agol_account.feature_service_url, agol_account.oauth_access_token)

    cloudwatch.delete_cloudwatch_rule(connection.cloudwatch_update_rule_name)
    connection.delete()


def schedule_source_agol(source, connection, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_custom_source_agol'
    update_agol_function = _lambda.get_lambda_function(function_name)

    update_agol_input = {
        'connection_uid': str(connection.uid),
    }

    short_name = organization.short_name
    rule_name = get_source_update_agol_rule_name(short_name, source.uid, settings.STAGE)

    _lambda.schedule_lambda_function(update_agol_function['arn'], update_agol_function['name'], update_agol_input,
                                 rule_name, settings.AGOL_UPDATE_RATE_MINUTES)

    connection.cloudwatch_update_rule_name = rule_name
    connection.save()


def get_source_update_agol_rule_name(short_name, source_uid, stage):

    stage = stage[:4]
    source_uid = str(source_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-source-agol-{source_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


def update_source_outputs(data, source, user):

    # output flag exists
    output_kml = data.get('output_kml')
    if output_kml is not None:

        # output flag is different than current state (kml rule names is alias for kml output enabled)
        if output_kml != (source.cloudwatch_update_kml_rule_names is not None):

            if output_kml:
                schedule_source_kml(source, user.organization)

            else:
                delete_source_kml(source)

    # user.agol_account will not be None, validated before
    output_agol = data.get('output_agol')
    if output_agol is not None:

        try:
            connection = DataConnection.objects.get(custom_source=source, agol_account=user.agol_account)
        except AgolAccount.DoesNotExist:
            connection = None
        except DataConnection.DoesNotExist:
            connection = None

        # output flag is different than current state (agol connection for account is alias for agol output enabled)
        if output_agol != (connection is not None):

            agol_account = user.agol_account

            if output_agol:
                # create a connection and schedule update
                connection = DataConnection.objects.create(organization=user.organization, account=user,
                                                           custom_source=source, agol_account=user.agol_account)
                schedule_source_agol(source, connection, user.organization)

                # create a layer and update the connection object
                agol.verify_access_token_valid(agol_account)
                layer_id = agol.create_custom_source_layer(source.name, source.description, agol_account.feature_service_url,
                                                      agol_account.oauth_access_token)
                connection.agol_layer_id = layer_id
                connection.save()

            else:
                # update layer name
                agol.verify_access_token_valid(agol_account)
                layer = agol.get_layer(connection.agol_layer_id, agol_account.feature_service_url, agol_account.oauth_access_token)
                agol.update_disconnected_layer_name(layer, agol_account.feature_service_url, agol_account.oauth_access_token)

                delete_source_agol(connection=connection)

