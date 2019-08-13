
import json
from rest_framework import serializers


class CaseInsensitiveEmailField(serializers.EmailField):
    def to_representation(self, value):
        return value.lower()


def get_updated_outputs(account, update_data):

    assert hasattr(account, 'outputs')

    outputs = json.loads(account.outputs)
    outputs['output_agol'] = update_data.pop('output_agol', outputs['output_agol'])
    outputs['output_database'] = update_data.pop('output_database', outputs['output_database'])
    outputs['output_kml'] = update_data.pop('output_kml', outputs['output_kml'])
    outputs = json.dumps(outputs)

    return outputs

