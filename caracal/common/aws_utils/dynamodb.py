
from django.conf import settings
from dynamodb_json import json_util as dynamodb_json_util
import json

from caracal.common.aws_utils import get_boto_client


# FIXME: can just use other boto3 method for accessing dynamodb content...
def create_dynamodb_credentials(org_short_name, username, password, permissions):
    assert isinstance(permissions, list)

    client = get_boto_client('dynamodb')
    item = {
        'organization': org_short_name,
        'credentials': [
            {
                'p': password,
                'u': username,
                'permissions': permissions
            }
        ]
    }

    dynamodb_json = dynamodb_json_util.dumps(item)
    dynamodb_json = json.loads(dynamodb_json)

    client.put_item(
        TableName=settings.S3_USER_CREDENTIALS_TABLE,
        Item=dynamodb_json
    )


def get_dynamodb_credentials(short_name):

    client = get_boto_client('dynamodb')

    item = client.get_item(
        TableName=settings.S3_USER_CREDENTIALS_TABLE,
        Key={
            'organization': {
                'S': short_name
            }
        }
    )

    item = dynamodb_json_util.loads(item)['Item']
    return item['credentials']


def get_global_config():

    client = get_boto_client('dynamodb')

    data = client.scan(
        TableName=settings.DYNAMO_CONFIG_TABLE_NAME,
    )

    items = dynamodb_json_util.loads(data['Items'])
    config = {item['name']: item['value'] for item in items}
    return config



