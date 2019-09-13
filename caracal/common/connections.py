
from caracal.common import constants
from outputs.models import DataConnection, DataOutput


def create_connections(organization, serializer_data, account_data):

    output_types = [output[0] for output in constants.OUTPUT_TYPES]
    for output_type in output_types:
        if output_type in serializer_data.keys() and serializer_data[output_type]:
            try:
                output = DataOutput.objects.get(organization=organization, type=output_type)
            except DataOutput.DoesNotExist:
                output = DataOutput.objects.create(organization=organization, type=output_type)

            DataConnection.objects.create(organization=organization, output=output, **account_data)


def delete_connections(account):
    assert hasattr(account, 'connections')

    for connection in account.connections.all():
        connection.is_active = False
        connection.save()


def get_outputs(account):

    outputs = {
        output_type: False
        for output_type in [o[0] for o in constants.OUTPUT_TYPES]
    }

    for connection in account.connections.filter(is_active=True):
        outputs[connection.output.type] = True

    return outputs


def update_connections(organization, serializer_data, account_data):

    output_types = [output[0] for output in constants.OUTPUT_TYPES]
    for output_type in output_types:
        print(output_type)
        # user wants to update this output
        if output_type in serializer_data.keys():
            # get/create output for both cases enabled/disabled
            try:
                output = DataOutput.objects.get(organization=organization, type=output_type)
            except DataOutput.DoesNotExist:
                output = DataOutput.objects.create(organization=organization, type=output_type)

            # output is enabled
            if serializer_data[output_type]:
                try:  # user already has a connection, set is_active to True
                    connection = DataConnection.objects.get(organization=organization,
                                                            output=output, **account_data)
                    connection.is_active = True
                    connection.save()
                except DataConnection.DoesNotExist:  # user does not have a connection, create one, is_active is True by default
                    DataConnection.objects.create(organization=organization, output=output, **account_data)

            # output is disabled
            else:
                try:  # user already has a connection, set is_active to False
                    connection = DataConnection.objects.get(organization=organization,
                                                            output=output, **account_data)
                    connection.is_active = False
                    connection.save()
                except:  # user does not have a connection, do nothing
                    pass