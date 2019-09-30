
from caracal.common import constants
from outputs.models import DataConnection


def create_connections(organization, data, account_data):

    if data.get('output_agol', False):
        pass



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


def update_connections(account_owner, serializer_data, account_data):

    organization = account_owner.organization

    output_types = [output[0] for output in constants.OUTPUT_TYPES]
    for output_type in output_types:

        # user wants to update this connection
        if output_type in serializer_data.keys():

            if output_type == 'output_agol':

                agol_account = account_owner.agol_account
                if agol_account is None:
                    print('agol account is None')

                # enable the connection
                if serializer_data[output_type]:

                    try:  # user already has a connection, set is_active to True
                        connection = DataConnection.objects.get(organization=organization,
                                                                agol_account=agol_account, **account_data)
                        connection.is_active = True
                        connection.save()
                    except DataConnection.DoesNotExist:  # user does not have a connection, create one, is_active is True by default
                        DataConnection.objects.create(organization=organization, agol_account=agol_account, **account_data)

                else:
                    try:  # user already has a connection, set is_active to False
                        connection = DataConnection.objects.get(organization=organization,
                                                                agol_account=agol_account, **account_data)
                        connection.is_active = False
                        connection.save()
                    except:  # user does not have a connection, do nothing
                        pass

            else:
                print(f'unknown output_type: {output_type}')
                pass
