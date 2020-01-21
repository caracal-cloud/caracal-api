from datetime import datetime, timezone
from django.conf import settings

from caracal.common import agol
from caracal.common.aws_utils import cloudwatch, _lambda
from outputs.models import AgolAccount, DataConnection


def delete_realtime_agol(agol_account=None, realtime_account=None, connection=None):
    "Deschedules Lambda function outputting to AGOL and deletes connection."

    # can be called with a connection, or accounts for connection lookup
    if connection is None:
        try:
            connection = DataConnection.objects.get(
                realtime_account=realtime_account, agol_account=agol_account
            )
        except DataConnection.DoesNotExist:
            print("connection does not exist, no problem")
            return

    agol_account = connection.agol_account

    agol.delete_feature_layers(
        layer_ids=[connection.agol_layer_id], #, connection.agol_individual_layer_id],
        feature_service_url=agol_account.feature_service_url,
        agol_account=agol_account,
    )

    # TODO: delete individual rule
    cloudwatch.delete_cloudwatch_rule(connection.cloudwatch_update_rule_name)

    connection.delete()


def delete_realtime_kml(realtime_account):
    "Deschedules Lambda function outputting to KML."

    if realtime_account.cloudwatch_update_kml_rule_names:
        update_kml_rule_names = realtime_account.cloudwatch_update_kml_rule_names.split(
            ","
        )
        for rule_name in update_kml_rule_names:
            cloudwatch.delete_cloudwatch_rule(rule_name)

    realtime_account.cloudwatch_update_kml_rule_names = None
    realtime_account.save()


def schedule_realtime_outputs(
    data, _type, source, realtime_account, user, agol_account=None
):
    "Schedules Lambda functions that outputs data from RDS to AGOL/KML."

    organization = user.organization

    if data.get("output_agol", False) and agol_account is not None:
        # create a connection and schedule update
        connection = DataConnection.objects.create(
            organization=organization,
            account=user,
            realtime_account=realtime_account,
            agol_account=agol_account,
        )

        _schedule_realtime_agol(
            type=_type,
            source=source,
            realtime_account=realtime_account,
            connection=connection,
            organization=organization,
        )

        feature_service = agol.get_or_create_caracal_feature_service(agol_account)
        layer_everything = agol.create_realtime_feature_layer(
            title=realtime_account.title,
            feature_service=feature_service,
            agol_account=agol_account,
        )

        """
        individual_layer_title = f"{realtime_account.title} - Individuals"
        layer_individuals = agol.create_realtime_feature_layer(
            title=individual_layer_title,
            feature_service=feature_service,
            agol_account=agol_account,
        )
        connection.agol_individual_layer_id = layer_individuals.id
        """

        connection.agol_layer_id = layer_everything.id
        connection.save()

    if data.get("output_kml", False):
        _schedule_realtime_kml(
            type=_type,
            source=source,
            realtime_account=realtime_account,
            organization=organization,
        )


def update_realtime_outputs(data, realtime_account, user):
    "Updates scheduling for Lambda functions."

    output_kml = data.get("output_kml", False)
    if output_kml:

        # output flag is different than current state (kml rule name exists is alias for kml output enabled)
        if output_kml != (
            realtime_account.cloudwatch_update_kml_rule_names is not None
        ):
            if output_kml:
                _schedule_realtime_kml(
                    type=realtime_account.type,
                    source=realtime_account.source,
                    realtime_account=realtime_account,
                    organization=user.organization,
                )
            else:
                delete_realtime_kml(realtime_account)

    # if True, user.agol_account will not be None, validated before
    output_agol = data.get("output_agol")
    if output_agol is not None:

        try:
            connection = DataConnection.objects.get(
                realtime_account=realtime_account, agol_account=user.agol_account
            )
        except AgolAccount.DoesNotExist:
            connection = None
        except DataConnection.DoesNotExist:
            connection = None

        # output flag is different than current state (agol connection for account is alias for agol output enabled)
        if output_agol != (connection is not None):

            agol_account = user.agol_account

            if output_agol:

                # create a connection and schedule update
                connection = DataConnection.objects.create(
                    organization=user.organization,
                    account=user,
                    realtime_account=realtime_account,
                    agol_account=user.agol_account,
                )

                # schedule the Lambda AGOL update
                _schedule_realtime_agol(
                    type=realtime_account.type,
                    source=realtime_account.source,
                    realtime_account=realtime_account,
                    connection=connection,
                    organization=user.organization,
                )

                # create the AGOL resources (service and layers)
                feature_service = agol.get_or_create_caracal_feature_service(
                    agol_account
                )
                layer_everything = agol.create_realtime_feature_layer(
                    title=realtime_account.title,
                    feature_service=feature_service,
                    agol_account=agol_account,
                )

                """
                individual_layer_title = f"{realtime_account.title} - Individuals"
                layer_individuals = agol.create_realtime_feature_layer(
                    title=individual_layer_title,
                    feature_service=feature_service,
                    agol_account=agol_account,
                )
                connection.agol_individual_layer_id = layer_individuals.id
                """

                # update the connection
                connection.agol_layer_id = layer_everything.id
                connection.save()

            else:
                delete_realtime_agol(connection=connection)


def _get_realtime_update_agol_rule_name(
    short_name, realtime_account_uid, stage, type, source
):
    "Gets Cloudfront rule name for updating AGOL."

    stage = stage[:4]
    type = type[:5]
    source = source[:5]
    realtime_account_uid = str(realtime_account_uid).split("-")[0][:4]

    rule_name = (
        f"{short_name}-{stage}-realtime-agol-{source}-{type}-{realtime_account_uid}"
    )
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


def _get_realtime_update_kml_rule_name(
    short_name, realtime_account_uid, stage, type, source, period
):
    "Gets the Cloudfront rule name for updating KML."

    stage = stage[:4]
    type = type[:5]
    source = source[:5]
    realtime_account_uid = str(realtime_account_uid).split("-")[0][:4]

    rule_name = (
        f"{short_name}-{stage}-rt-kml-{source}-{type}-{period}-{realtime_account_uid}"
    )
    rule_name = rule_name.lower()

    print("rule_name", rule_name, len(rule_name))

    assert len(rule_name) < 64
    return rule_name


def _schedule_realtime_agol(type, source, realtime_account, connection, organization):
    "Schedules Lambda function that gets data from RDS and outputs to AGOL."

    # TODO: schedule individual

    function_name = f"caracal_{settings.STAGE.lower()}_update_realtime_agol"
    update_agol_function = _lambda.get_lambda_function(function_name)

    update_agol_input = {
        "connection_uid": str(connection.uid),
    }

    short_name = organization.short_name
    rule_name = _get_realtime_update_agol_rule_name(
        short_name, realtime_account.uid, settings.STAGE, type, source
    )

    _lambda.schedule_lambda_function(
        update_agol_function["arn"],
        update_agol_function["name"],
        update_agol_input,
        rule_name,
        settings.AGOL_UPDATE_RATE_MINUTES,
    )

    connection.cloudwatch_update_rule_name = rule_name
    connection.save()


def _schedule_realtime_kml(type, source, realtime_account, organization):
    "Schedules Lambda function that gets data from RDS and outputs to KML/S3."

    function_name = f"caracal_{settings.STAGE.lower()}_update_realtime_kml"
    update_kml_function = _lambda.get_lambda_function(function_name)

    rule_names = list()
    for period in settings.KML_PERIOD_HOURS:

        rate_minutes = int(period / 2.5)  # longer for larger periods

        update_kml_input = {
            "rt_account_uid": str(realtime_account.uid),
            "period_hours": period,
        }

        short_name = organization.short_name
        # TODO: possibly use non-unique rule name...
        rule_name = _get_realtime_update_kml_rule_name(
            short_name, realtime_account.uid, settings.STAGE, type, source, period
        )
        rule_names.append(rule_name)

        _lambda.schedule_lambda_function(
            update_kml_function["arn"],
            update_kml_function["name"],
            update_kml_input,
            rule_name,
            rate_minutes,
        )

    realtime_account.cloudwatch_update_kml_rule_names = ",".join(rule_names)
    realtime_account.save()
