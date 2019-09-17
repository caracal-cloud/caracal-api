
import stripe
import time


def create_customer(account):
    # source will create a new source object,
    # make it the new customer default source,
    # and delete the old customer default if one exists.

    try:
        customer = stripe.Customer.create(
            email=account.email,
            name=account.name,
            phone=account.phone_number
        )
        return {
            'customer_id': customer['id']
        }
    except stripe.error.InvalidRequestError as e:
        print(e)
        return {
            'error': 'invalid_request',
            'message': 'invalid parameters were supplied'
        }


def create_complete_trial_subscription(customer_id):

    subscription = stripe.Subscription.create(
        customer = customer_id,
        items = [
            {
                'plan': 'plan_FntBno8sVRuQrU' # Trial plan, 14 day trial, $1 so payment fails
            }
        ],
        trial_period_days = 14
    )

    print(subscription)




