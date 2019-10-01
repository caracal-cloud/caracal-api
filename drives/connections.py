
from django.conf import settings

from caracal.common import aws

# Get data

def schedule_drives_get_data(drive_account, organization):

    # caracal_production_get_static_google_google_sheet_data
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


# Update outputs

def schedule_drives_outputs(data, drive_account, user, agol_account=None):

    if data.get('output_agol', False) and agol_account is not None:
        # create a connection and schedule update
        connection = DataConnection.objects.create(organization=organization, account=user,
                                                   drive_account=drive_account, agol_account=agol_account)
        schedule_drives_agol(species, connection, organization)


    if data.get('output_kml', False):
        schedule_drives_kml(drive_account, organization)


# Update KML

def schedule_drives_kml(realtime_account, organization):
    pass


def get_drives_update_kml_rule_name(org_short_name, stage, provider, file_type, period):

    stage = stage[:4]
    provider = provider[:10]
    file_type = file_type[:10]

    rule_name = f'{org_short_name}-{stage}-drives-kml-{provider}-{file_type}-{period}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


# Update ArcGIS Online

def schedule_collars_agol(species, connection, organization):
    pass


def get_drives_update_agol_rule_name(org_short_name, stage, provider, file_type):

    stage = stage[:4]
    provider = provider[:10]
    file_type = file_type[:10]

    rule_name = f'{org_short_name}-{stage}-drives-agol-{provider}-{file_type}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name

