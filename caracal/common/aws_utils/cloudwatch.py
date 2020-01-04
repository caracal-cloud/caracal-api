
from caracal.common.aws_utils import get_boto_client


def delete_cloudwatch_rule(rule_name):

    if rule_name is None:
        return

    client = get_boto_client('events')
    client.remove_targets(Rule=rule_name, Ids=["1"])
    client.delete_rule(Name=rule_name)


