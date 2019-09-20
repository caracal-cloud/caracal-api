
from rest_framework import serializers


class GetPlansUrlQueryParamsSerializer(serializers.Serializer):
    filter_is_paid = serializers.BooleanField(required=False)


class UpdatePaymentMethodSerializer(serializers.Serializer):
    card_token = serializers.CharField()


class UpdatePlanAndPaymentMethodSerializer(serializers.Serializer):

    card_token = serializers.CharField()
    plan_id = serializers.CharField()


class UpdateSubscriptionSerializer(serializers.Serializer):
    new_plan_id = serializers.CharField()


