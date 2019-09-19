
import json
from rest_framework import permissions, status, generics, views
from rest_framework.response import Response
import stripe

from account.models import Organization
from auth.backends import CognitoAuthentication
from billing import serializers
from caracal.common import stripe_utils


class GetPlansView(views.APIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = serializers.GetPlansUrlQueryParamsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)

        filter_is_paid = serializer.data.get('filter_is_paid', False)

        plans = stripe_utils.get_plans(filter_is_paid)
        plans = sorted(plans, key=lambda k: k['amount'])

        return Response(data=plans, status=status.HTTP_200_OK)


class StripeWebhookView(views.APIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):

        try:
            event = stripe.Event.construct_from(request.data, stripe.api_key)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            organization = Organization.objects.get(stripe_customer_id=event.data.object.customer)
        except Organization.DoesNotExist:
            print('Organization not found: ' + event.data.object.customer)
            # TODO: capture error
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            previous_status = organization.stripe_subscription_status

        if event.type == 'customer.subscription.updated':

            if event.data.object.id == organization.stripe_subscription_id:
                print(f'{organization.name} changing from {previous_status} to {event.data.object.status}')
                organization.stripe_subscription_status = event.data.object.status
                organization.save()

            return Response(status=status.HTTP_200_OK)

        elif event.type == 'invoice.payment_failed':
            return Response(status=status.HTTP_200_OK)

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class UpdatePaidSubscriptionView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateSubscriptionSerializer

    def post(self, request):
        serializer = serializers.UpdateSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization
        subscription_id = organization.stripe_subscription_id

        new_plan_id = serializer.data['new_plan_id']

        current_subscription = stripe_utils.get_subscription(subscription_id)
        if current_subscription['plan_name'] == 'Trial':
            return Response({
                'error': 'plan_error',
                'message': 'Paid plan required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        elif current_subscription['plan_id'] == new_plan_id:
            return Response({
                'error': 'plan_error',
                'message': 'Please select a different plan.'
            }, status=status.HTTP_400_BAD_REQUEST)

        stripe_utils.update_subscription(subscription_id, new_plan_id, current_subscription['item_id'])

        organization.stripe_plan_id = new_plan_id
        organization.save()

        return Response(status=status.HTTP_200_OK)


class UpdatePaymentMethodView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdatePaymentMethodSerializer


    def post(self, request):
        serializer = serializers.UpdatePaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization

        card_token = serializer.data['card_token']

        card_res = stripe_utils.update_customer_payment_method(card_token, organization.stripe_customer_id)
        if 'error' in card_res.keys():
            return Response(card_res, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)


class UpdateTrialToPaidSubscriptionView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdateTrialToPaidSubscriptionSerializer

    def post(self, request):
        serializer = serializers.UpdateTrialToPaidSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization

        # make sure currently trialing
        current_subscription = stripe_utils.get_subscription(organization.stripe_subscription_id)
        if current_subscription['plan_name'] != 'Trial':
            return Response({
                'error': 'plan_error',
                'message': 'Must have Trial account.'
            }, status=status.HTTP_400_BAD_REQUEST)

        card_token = serializer.data['card_token']
        plan_id = serializer.data['plan_id']

        # add new card
        card_res = stripe_utils.update_customer_payment_method(card_token, organization.stripe_customer_id)
        if 'error' in card_res.keys():
            return Response(card_res, status=status.HTTP_400_BAD_REQUEST)

        # create a new paid subscription
        subscription_res = stripe_utils.create_paid_subscription(organization.stripe_customer_id, plan_id)
        if 'error' in subscription_res.keys():
            stripe_utils.delete_subscription(subscription_res['id'])
            del subscription_res['id']
            return Response(subscription_res, status=status.HTTP_400_BAD_REQUEST)

        # remove trial subscription
        stripe_utils.delete_subscription(organization.stripe_subscription_id)

        # update new paid subscription and plan
        organization.stripe_plan_id = plan_id
        organization.stripe_subscription_id = subscription_res['id']
        organization.stripe_subscription_status = subscription_res['status']
        organization.save()

        return Response(status=status.HTTP_201_CREATED)





