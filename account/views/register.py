
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from account import serializers
from caracal.common import stripe


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
        customer_res = stripe.create_customer(account)
        if 'error' in customer_res.keys():
            return Response(customer_res, status=status.HTTP_400_BAD_REQUEST)

        customer_id = customer_res['customer_id']
        account.organization.stripe_customer_id = customer_id
        account.organization.save()

        # subscribe customer to Complete plan with trial
        stripe.create_complete_trial_subscription(customer_id)

        return Response(status=status.HTTP_201_CREATED)

