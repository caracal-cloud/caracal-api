
import json

from caracal.common.aws_utils import get_boto_client


def put_firehose_record(payload, stream_name):

    # newline is the record deliminator so remove it from inside the record
    data = json.dumps(payload).replace('\n', '')

    client = get_boto_client('firehose')
    client.put_record(
        DeliveryStreamName=stream_name,
        Record={
            'Data': data + '\n'
        }
    )
