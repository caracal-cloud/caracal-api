
from django.conf import settings

from caracal.common import aws
from outputs.models import AgolAccount, DataConnection


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

    organization = user.organization

    if data.get('output_agol', False) and agol_account is not None:
        # create a connection and schedule update
        connection = DataConnection.objects.create(organization=organization, account=user,
                                                   drive_account=drive_account, agol_account=agol_account)
        schedule_drives_agol(drive_account, connection, organization)

    if data.get('output_kml', False):
        schedule_drives_kml(drive_account, organization)


# Update KML

def delete_drives_kml(drive_account):

    if drive_account.cloudwatch_update_kml_rule_names:
        update_kml_rule_names = drive_account.cloudwatch_update_kml_rule_names.split(',')
        for rule_name in update_kml_rule_names:
            aws.delete_cloudwatch_rule(rule_name)

    drive_account.cloudwatch_update_kml_rule_names = None
    drive_account.save()


def schedule_drives_kml(drive_account, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_static_kml'
    update_kml_function = aws.get_lambda_function(function_name)

    print('kml function_name', function_name)

    rule_names = []
    for period in settings.KML_PERIOD_HOURS:

        rate_minutes = int(period / 2.5) # longer for larger periods

        update_kml_input = {
            'drive_account_uid': str(drive_account.uid),
            'period_hours': period
        }

        short_name = organization.short_name
        rule_name = get_drives_update_kml_rule_name(short_name, drive_account.uid, settings.STAGE, drive_account.provider,
                                                    drive_account.file_type, period)
        rule_names.append(rule_name)

        print('kml rule_name', rule_name)

        aws.schedule_lambda_function(update_kml_function['arn'], update_kml_function['name'], update_kml_input,
                                     rule_name, rate_minutes)

    # append to cloudwatch_update_kml_rule_names
    drive_account.cloudwatch_update_kml_rule_names = ','.join(rule_names)
    drive_account.save()


def get_drives_update_kml_rule_name(short_name, drive_account_uid, stage, provider, file_type, period):

    stage = stage[:4]
    provider = provider[:10]
    file_type = file_type[:10]
    drive_account_uid = str(drive_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-drives-kml-{provider}-{file_type}-{period}-{drive_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name


# Update ArcGIS Online

def delete_drives_agol(agol_account=None, drive_account=None, connection=None):

    if connection is None:
        try:
            connection = DataConnection.objects.get(drive_account=drive_account, agol_account=agol_account)
        except DataConnection.DoesNotExist:
            print('connection does not exist, no problem')
            return

    aws.delete_cloudwatch_rule(connection.cloudwatch_update_rule_name)
    connection.delete()


def schedule_drives_agol(drive_account, connection, organization):

    function_name = f'caracal_{settings.STAGE.lower()}_update_static_agol'
    update_agol_function = aws.get_lambda_function(function_name)

    print('agol function_name', function_name)

    update_agol_input = {
        'connection_uid': str(connection.uid),
    }

    short_name = organization.short_name
    rule_name = get_drives_update_agol_rule_name(short_name, drive_account.uid, settings.STAGE, drive_account.provider,
                                                 drive_account.file_type)

    print('agol rule_name', rule_name)


    aws.schedule_lambda_function(update_agol_function['arn'], update_agol_function['name'], update_agol_input,
                                 rule_name, settings.AGOL_UPDATE_RATE_MINUTES)

    connection.cloudwatch_update_rule_name = rule_name
    connection.save()

def get_drives_update_agol_rule_name(short_name, drive_account_uid, stage, provider, file_type):

    stage = stage[:4]
    provider = provider[:10]
    file_type = file_type[:10]
    drive_account_uid = str(drive_account_uid).split('-')[0][:4]

    rule_name = f'{short_name}-{stage}-drives-agol-{provider}-{file_type}-{drive_account_uid}'
    rule_name = rule_name.lower()

    assert len(rule_name) < 64
    return rule_name



def update_drives_outputs(data, drive_account, user):

    output_kml = data.get('output_kml')
    if output_kml is not None:

        if output_kml != (drive_account.cloudwatch_update_kml_rule_names is not None):

            if output_kml:
                schedule_drives_kml(drive_account, user.organization)

            else:
                delete_drives_kml(drive_account)

    output_agol = data.get('output_agol')
    if output_agol is not None:

        try:
            connection = DataConnection.objects.get(drive_account=drive_account, agol_account=user.agol_account)
        except AgolAccount.DoesNotExist:
            connection = None
        except DataConnection.DoesNotExist:
            connection = None

        if output_agol != (connection is not None):

            if output_agol:
                connection = DataConnection.objects.create(organization=user.organization, account=user,
                                                           drive_account=drive_account,
                                                           agol_account=user.agol_account)
                schedule_drives_agol(drive_account, connection, user.organization)

            else:
                delete_drives_agol(connection=connection)

















