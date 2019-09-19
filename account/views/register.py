
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from account import serializers
from caracal.common import stripe_utils


class RegisterView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RegisterSerializer

    @swagger_auto_schema(responses={
        status.HTTP_201_CREATED: '',
        status.HTTP_400_BAD_REQUEST: 'email_already_exists, invalid_organization_short_name, '
                                     'organization_short_name_already_exists',
    }, security=[], operation_id='account - register')
    def post(self, request):

        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = serializer.save()
        if isinstance(account, Response): # there was an error
            return account

        # create a Stripe customer and save id to organization
        customer_res = stripe_utils.create_customer(account.email, account.name, account.phone_number)
        if 'error' in customer_res.keys():
            return Response(customer_res, status=status.HTTP_400_BAD_REQUEST)

        customer_id = customer_res['customer_id']
        account.organization.stripe_customer_id = customer_id
        account.organization.save() # save customer_id for webhooks

        # subscribe customer to Trial plan
        trial_plan = stripe_utils.get_plan('Trial')
        subscription = stripe_utils.create_trial_subscription(customer_id, plan_id=trial_plan['id'])

        account.organization.stripe_plan_id = trial_plan['id']
        account.organization.stripe_subscription_id = subscription['id']
        account.organization.stripe_subscription_status = subscription['status']
        account.organization.save()

        return Response(status=status.HTTP_201_CREATED)

