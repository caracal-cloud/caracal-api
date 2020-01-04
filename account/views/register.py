
from django.conf import settings
from django.db import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from account import serializers
from account.models import Organization, Account
from caracal.common import stripe_utils, names
from caracal.common.aws_utils import exceptions
from caracal.common.aws_utils import cognito


class RegisterView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.RegisterSerializer

    @swagger_auto_schema(responses={
        status.HTTP_201_CREATED: '',
        status.HTTP_400_BAD_REQUEST: 'email_already_exists, invalid_organization_short_name, '
                                     'organization_short_name_already_exists',
    }, security=[], operation_id='account - register')
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        organization_name = data['organization_name']
        account_name = data['account_name']
        account_email = data['account_email']
        password = data['account_password']

        account_phone_number = data.get('account_phone_number')
        organization_short_name = names.generate_unique_short_name()

        organization = Organization.objects.create(name=organization_name, short_name=organization_short_name)

        try:
            uid_cognito = cognito.create_user(account_email, password, registration_method='email')
            #cognito.confirm_account(account_email) not doing this yet...

            account = Account.objects.create(uid_cognito=uid_cognito, organization=organization, email=account_email,
                                             name=account_name, phone_number=account_phone_number, is_admin=True)

        except (IntegrityError, exceptions.UsernameExistsException):
            organization.delete()
            return Response({
                'error': 'email_already_exists',
            }, status=status.HTTP_400_BAD_REQUEST)
        except (exceptions.ParamValidationError, exceptions.InvalidParameterException):
            organization.delete()
            return Response({
                'error': 'invalid_parameter',
            }, status=status.HTTP_400_BAD_REQUEST)

        """
        # create a Stripe customer and save id to organization
        customer_res = stripe_utils.create_customer(account.email, account.name, account.phone_number)
        if 'error' in customer_res.keys():
            return Response(customer_res, status=status.HTTP_400_BAD_REQUEST)

        customer_id = customer_res['customer_id']
        account.organization.stripe_customer_id = customer_id
        account.organization.save() # save customer_id for webhooks

        # subscribe customer to Trial plan
        plan = stripe_utils.get_plan('Individual')
        subscription = stripe_utils.create_subscription(customer_id, plan_id=plan['id'])

        account.organization.stripe_plan_id = plan['id']
        account.organization.stripe_subscription_id = subscription['id']
        account.organization.stripe_subscription_status = subscription['status']
        account.organization.save()        
        """

        #tokens = cognito.sign_in_user(account_email, password)

        return Response({
            'account_uid': str(account.uid_cognito),
            #'access_token': tokens['access_token'],
            #'refresh_token': tokens['refresh_token']
        }, status=status.HTTP_201_CREATED)
