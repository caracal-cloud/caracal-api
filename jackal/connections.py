from datetime import datetime, timezone
from django.conf import settings

from caracal.common import agol
from caracal.common.aws_utils import cloudwatch, _lambda
from outputs.models import AgolAccount, DataConnection


def schedule_jackal_outputs(data, network, user, agol_account=None):

    organization = user.organization

    if data.get("output_agol", False) and agol_account is not None:

        # 1. Create a connection
        connection = DataConnection.objects.create(
            organization=organization,
            account=user,
            jackal_network=network,
            agol_account=agol_account,
        )

        # 2. Schedule Lambda function to update AGOL
        _schedule_jackal_agol(
            network=network,
            connection=connection,
            organization=organization
        )

        # 3. Create feature service and layers in AGOL
        feature_service = agol.get_or_create_caracal_feature_service(agol_account)
        feature_layer = agol.create_jackal_feature_layer(
            title='Jackal Locations',
            feature_service=feature_service,
            agol_account=agol_account,
        )

        # 4. Update connection with layer ID
        connection.agol_layer_id = feature_layer.id
        connection.save()


    if data.get("output_kml", False):
        _schedule_jackal_kml(network, organization)


def _get_jackal_update_agol_rule_name(short_name, jackal_network_uid, stage):

    stage = stage[:4]
    jackal_network_uid = str(jackal_network_uid)[:4]

    rule_name = f"{short_name}-{stage}-jackal-agol-{jackal_network_uid}"
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


def _schedule_jackal_agol(network, connection, organization):

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

    realtime_account.cloudwatch_update_kml_rule_names = ",".join(rule_names)
    realtime_account.save()
