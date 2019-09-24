
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
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            previous_status = organization.stripe_subscription_status

        if event.type == 'customer.subscription.updated':

            new_status = event.data.object.status
            if event.data.object.id == organization.stripe_subscription_id:
                print(f'{organization.name} changing from {previous_status} to {new_status}')
                organization.stripe_subscription_status = new_status
                organization.save()

            return Response(status=status.HTTP_200_OK)

        elif event.type == 'invoice.payment_succeeded':
            # if the organization has paid a non-0 invoice (even with discount),
            # mark their account as not trialing (current or expired trial)
            subtotal = event.data.object.subtotal
            if subtotal > 0:
                print(f'{organization.name} changing is_trialing to False')
                organization.is_trialing = False
                organization.save()

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

        if organization.is_trialing:
            return Response({
                'error': 'plan_error',
                'message': 'You cannot change plans if you are still trialing.'
            }, status=status.HTTP_400_BAD_REQUEST)

        new_plan_id = serializer.data['new_plan_id']

        current_subscription = stripe_utils.get_subscription(subscription_id)
        if current_subscription['plan_id'] == new_plan_id:
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
        coupon = serializer.data.get('coupon')

        # coupon must be applied before adding payment method to avoid charge
        if coupon is not None:
            coupon_res = stripe_utils.update_subscription_coupon(organization.stripe_subscription_id, coupon)
            if 'error' in coupon_res:
                return Response(coupon_res, status=status.HTTP_400_BAD_REQUEST)


        card_res = stripe_utils.update_customer_payment_method(card_token, organization.stripe_customer_id)
        if 'error' in card_res.keys():
            return Response(card_res, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)


class UpdatePlanAndPaymentMethodView(generics.GenericAPIView):

    authentication_classes = [CognitoAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UpdatePlanAndPaymentMethodSerializer

    def post(self, request):
        serializer = serializers.UpdatePlanAndPaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        organization = user.organization
        subscription_id = organization.stripe_subscription_id

        card_token = serializer.data['card_token']
        coupon = serializer.data.get('coupon')
        plan_id = serializer.data['plan_id']

        # coupon must be applied before adding payment method to avoid charge
        if coupon is not None:
            coupon_res = stripe_utils.update_subscription_coupon(subscription_id, coupon)
            if 'error' in coupon_res:
                return Response(coupon_res, status=status.HTTP_400_BAD_REQUEST)

        # add new card
        card_res = stripe_utils.update_customer_payment_method(card_token, organization.stripe_customer_id)
        if 'error' in card_res.keys():
            return Response(card_res, status=status.HTTP_400_BAD_REQUEST)

        # update subscription
        current_subscription = stripe_utils.get_subscription(subscription_id)

        if plan_id != organization.stripe_plan_id:
            # handle immediate payment failure
            subscription_res = stripe_utils.update_subscription(subscription_id, plan_id, current_subscription['item_id'])
            if 'error' in subscription_res:
                # if it fails, then revert to previous subscription
                trial_end = int(current_subscription['trial_end'].timestamp()) if 'trial_end' in current_subscription.keys() else 'now'
                print('previous trial_end', trial_end)
                stripe_utils.update_subscription(subscription_id, current_subscription['plan_id'], current_subscription['item_id'], trial_end=trial_end)
                return Response(subscription_res, status=status.HTTP_400_BAD_REQUEST)

            organization.stripe_plan_id = plan_id
            organization.save()

        return Response(status=status.HTTP_201_CREATED)





