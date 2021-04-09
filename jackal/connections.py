from datetime import datetime, timezone
from django.conf import settings

from caracal.common import agol
from caracal.common.aws_utils import cloudwatch, _lambda
from outputs.models import AgolAccount, DataConnection, JackalAgolConnection


def delete_jackal_agol(agol_account=None, network=None, connection=None):
    
    if connection is None:
        try:
            connection = DataConnection.objects.get(
                jackal_network=network, agol_account=agol_account
            )
        except DataConnection.DoesNotExist:
            print("connection does not exist")
            return

    agol_account = connection.agol_account

    jackal_agol_connection = connection.jackal_agol_connection

    agol.delete_feature_layers(
        layer_ids=[
            connection.agol_layer_id,
            jackal_agol_connection.jackal_calls_table_id,
            jackal_agol_connection.jackal_contacts_table_id,
            jackal_agol_connection.jackal_texts_table_id,
            jackal_agol_connection.jackal_wa_calls_table_id,
            jackal_agol_connection.jackal_wa_groups_table_id,
            jackal_agol_connection.jackal_wa_messages_table_id,
            jackal_agol_connection.jackal_wa_users_table_id
        ],
        feature_service_url=agol_account.feature_service_url,
        agol_account=agol_account,
    )

    cloudwatch.delete_cloudwatch_rule(connection.cloudwatch_update_rule_name)

    jackal_agol_connection.delete()
    connection.delete()


def delete_jackal_kml(network):
    
    if network.cloudwatch_update_kml_rule_names:
        update_kml_rule_names = network.cloudwatch_update_kml_rule_names.split(",")
        for rule_name in update_kml_rule_names:
            cloudwatch.delete_cloudwatch_rule(rule_name)

    network.cloudwatch_update_kml_rule_names = None
    network.save()


def schedule_jackal_excel(network, organization):

    function_name = f"caracal_{settings.STAGE.lower()}_create_jackal_excel"
    create_excel_function = _lambda.get_lambda_function(function_name)
    
    create_excel_input = {
        "network_uid": str(network.uid),
    }

    rule_name = _get_jackal_create_excel_rule_name(
        short_name=organization.short_name,
        jackal_network_uid=network.uid,
        stage=settings.STAGE
    )

    _lambda.schedule_lambda_function(
        fn_arn=create_excel_function["arn"],
        fn_name=create_excel_function["name"],
        rule_input=create_excel_input,
        rule_name=rule_name,
        rate_minutes=settings.JACKAL_EXCEL_UPDATE_RATE_MINTES
    )

    network.cloudwatch_update_excel_rule_name = rule_name
    network.save()


def schedule_jackal_kml(network, organization):

    function_name = f"caracal_{settings.STAGE.lower()}_update_jackal_kml"
    update_kml_function = _lambda.get_lambda_function(function_name)

    rule_names = list()
    for hours in [24, 36, 168, 720, 8760]:
        update_kml_input = {
            'period_hours': hours,
            'jackal_network_uid': str(network.uid)
        }

        short_name = organization.short_name
        rule_name = _get_jackal_update_kml_rule_name(
            short_name=short_name, 
            jackal_network_uid=network.uid, 
            stage=settings.STAGE, 
            period=hours
        )
        rule_names.append(rule_name)

        _lambda.schedule_lambda_function(
            fn_arn=update_kml_function["arn"],
            fn_name=update_kml_function["name"],
            rule_input=update_kml_input,
            rule_name=rule_name,
            rate_minutes=settings.JACKAL_KML_UPDATE_RATE_MINTES
        )

    network.cloudwatch_update_kml_rule_names = ",".join(rule_names)
    network.save()


def schedule_jackal_outputs(data, network, user, agol_account=None):

    organization = user.organization

    if data.get("output_agol", False) and agol_account is not None:
        _create_agol_resources(network, user)

    if data.get("output_kml", False):
        _schedule_jackal_kml(network, organization)


def update_jackal_outputs(data, network, user):

    output_kml = data.get("output_kml", False)
    if output_kml:

        if output_kml != network.cloudwatch_update_kml_rule_names is not None:
            if output_kml:
                _schedule_jackal_kml(network, user.organization)
            else:
                delete_jackal_kml(network)

    # if True, user.agol_account will not be None, validated before
    output_agol = data.get("output_agol")
    if output_agol is not None:
        try:
            connection = DataConnection.objects.get(
                jackal_network=network,
                agol_account=user.agol_account
            )
        except (AgolAccount.DoesNotExist, DataConnection.DoesNotExist):
            connection = None

        # output_agol is different from the current state
        if output_agol != (connection is not None):

            if output_agol:
                _create_agol_resources(network, user)
            else:
                delete_jackal_agol(connection=connection)


def _create_agol_resources(network, user):

    agol_account = user.agol_account

    # create the AGOL resources (service and layers)
    feature_service = agol.get_or_create_caracal_feature_service(agol_account)
    locations_layer = agol.create_jackal_feature_layer(
        title='Jackal Locations',
        feature_service=feature_service,
        agol_account=agol_account,
    )

    # create a connection and schedule update
    jackal_agol_connection = _create_jackal_agol_connection(feature_service, agol_account)
    connection = DataConnection.objects.create(
        organization=user.organization,
        account=user,
        jackal_network=network,
        agol_account=agol_account,
        agol_layer_id=locations_layer.id,
        jackal_agol_connection=jackal_agol_connection
    )

    # schedule the Lambda AGOL update
    _schedule_update_jackal_agol(
        network=network,
        connection=connection,
        organization=user.organization
    )

def _create_jackal_agol_connection(feature_service, agol_account):

    jackal_agol_connection = JackalAgolConnection()

    calls_table = agol.create_jackal_calls_table(feature_service, agol_account)
    jackal_agol_connection.jackal_calls_table_id = calls_table.id

    contacts_table = agol.create_jackal_contacts_table(feature_service, agol_account)
    jackal_agol_connection.jackal_contacts_table_id = contacts_table.id

    texts_table = agol.create_jackal_texts_table(feature_service, agol_account)
    jackal_agol_connection.jackal_texts_table_id = texts_table.id

    wa_calls_table = agol.create_jackal_wa_calls_table(feature_service, agol_account)
    jackal_agol_connection.jackal_wa_calls_table_id = wa_calls_table.id

    wa_groups_table = agol.create_jackal_wa_groups_table(feature_service, agol_account)
    jackal_agol_connection.jackal_wa_groups_table_id = wa_groups_table.id

    wa_messages_table = agol.create_jackal_wa_messages_table(feature_service, agol_account)
    jackal_agol_connection.jackal_wa_messages_table_id = wa_messages_table.id

    wa_users_table = agol.create_jackal_wa_users_table(feature_service, agol_account)
    jackal_agol_connection.jackal_wa_users_table_id = wa_users_table.id

    jackal_agol_connection.save()
    return jackal_agol_connection


def _get_jackal_update_agol_rule_name(short_name, jackal_network_uid, stage):

    stage = stage[:4]
    jackal_network_uid = str(jackal_network_uid)[:4]

    rule_name = f"{short_name}-{stage}-jackal-agol-{jackal_network_uid}"
    rule_name = rule_name.lower()

    print("rule_name", rule_name, len(rule_name))

    assert len(rule_name) < 64
    return rule_name


def _get_jackal_create_excel_rule_name(short_name, jackal_network_uid, stage):

    stage = stage[:4]
    jackal_network_uid = str(jackal_network_uid)[:4]

    rule_name = f"{short_name}-{stage}-jackal-excel-{jackal_network_uid}"
    rule_name = rule_name.lower()

    print("rule_name", rule_name, len(rule_name))

    assert len(rule_name) < 64
    return rule_name


def _get_jackal_update_kml_rule_name(short_name, jackal_network_uid, stage, period):
    "Gets the Cloudfront rule name for updating KML."

    stage = stage[:4]
    jackal_network_uid = str(jackal_network_uid)[:4]

    rule_name = f"{short_name}-{stage}-jackal-kml-{period}-{jackal_network_uid}"
    rule_name = rule_name.lower()

    print("rule_name", rule_name, len(rule_name))

    assert len(rule_name) < 64
    return rule_name


def _schedule_update_jackal_agol(network, connection, organization):

    function_name = f"caracal_{settings.STAGE.lower()}_update_jackal_agol"
    update_agol_function = _lambda.get_lambda_function(function_name)

    update_agol_input = {
        "connection_uid": str(connection.uid),
    }

    rule_name = _get_jackal_update_agol_rule_name(
        short_name=organization.short_name,
        jackal_network_uid=network.uid,
        stage=settings.STAGE
    )

    _lambda.schedule_lambda_function(
        fn_arn=update_agol_function["arn"],
        fn_name=update_agol_function["name"],
        rule_input=update_agol_input,
        rule_name=rule_name,
        rate_minutes=settings.AGOL_UPDATE_RATE_MINUTES
    )

    connection.cloudwatch_update_rule_name = rule_name
    connection.save()


def _schedule_jackal_kml(network, organization):

    function_name = f"caracal_{settings.STAGE.lower()}_update_jackal_kml"
    update_kml_function = _lambda.get_lambda_function(function_name)

    rule_names = list()
    for period in settings.KML_PERIOD_HOURS:

        rate_minutes = int(period / 2.5)  # longer for larger periods

        update_kml_input = {
            "jackal_network_uid": str(network.uid),
            "period_hours": period,
        }

        rule_name = _get_jackal_update_kml_rule_name(
            short_name=organization.short_name,
            jackal_network_uid=network.uid,
            stage=settings.STAGE,
            period=period
        )

        rule_names.append(rule_name)

        _lambda.schedule_lambda_function(
            fn_arn=update_kml_function["arn"],
            fn_name=update_kml_function["name"],
            rule_input=update_kml_input,
            rule_name=rule_name,
            rate_minutes=rate_minutes
        )

    network.cloudwatch_update_kml_rule_names = ",".join(rule_names)
    network.save()
