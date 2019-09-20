
from datetime import datetime, timezone
import stripe
import time


def create_customer(email, name, phone_number):

    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            phone=phone_number
        )
        return {
            'customer_id': customer['id']
        }
    except stripe.error.InvalidRequestError as e:
        return {
            'error': 'invalid_request',
            'message': 'invalid parameters were supplied'
        }


def create_subscription(customer_id, plan_id):

    subscription = stripe.Subscription.create(
        customer = customer_id,
        items = [
            {
                'plan': plan_id
            }
        ],
        trial_period_days = 14
        #trial_end=int(time.time()) + 30  # testing
    )

    return {
        'id': subscription.id,
        'status': subscription.status
    }


def create_paid_subscription(customer_id, plan_id):

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[
            {
                'plan': plan_id,
            },
        ],
        expand = ['latest_invoice.payment_intent'],
    )

    subscription_status = subscription.status
    payment_status = subscription.latest_invoice.payment_intent.charges.data[0].status

    if subscription_status == 'incomplete':

        if payment_status in ['failed', 'requires_payment_method']:
            return {
                'id': subscription.id,
                'error': 'payment_error',
                'message': 'There was an error charging your card. Please try again or use another card.'
            }

        elif payment_status == 'requires_action':
            return {
                'id': subscription.id,
                'error': 'payment_error',
                'message': 'Additional action required.'
            }

        else:
            raise ValueError('unknown payment_status: ' + payment_status)

    elif subscription_status in ['active', 'trialing']:
        return {
            'id': subscription.id,
            'status': subscription_status
        }

    else:
        raise ValueError('unknown subscription_status: ' + subscription_status)


def delete_customer(customer_id):

    if customer_id is None:
        return True

    try:
        stripe.Customer.delete(customer_id)
    except stripe.error.InvalidRequestError:
        return False
    else:
        return True


def delete_subscription(subscription_id):
    stripe.Subscription.delete(subscription_id)


def get_customer(customer_id):

    try:
        customer = stripe.Customer.retrieve(customer_id)
    except stripe.error.InvalidRequestError as e:
        print(e)
        return None
    else:
        return customer


def get_plan(name):

    plans = stripe.Plan.list(active=True, limit=100, product="prod_Fn5j0maJ1hVAWx")
    plans = plans['data']

    for plan in plans:
        if plan['nickname'] == name:
            return {
                'id': plan['id'],
                'name': plan['nickname'],
                'amount': plan['amount'] / 100,
                'currency': plan['currency'],
                'interval': plan['interval'],
                'trial_days': plan['trial_period_days']
            }



def get_plans(filter_is_paid=False):

    plans = stripe.Plan.list(active=True, limit=100, product="prod_Fn5j0maJ1hVAWx")
    plans = plans['data']

    if filter_is_paid:
        plans = [plan for plan in plans if plan['nickname'] != 'Trial']

    plans = [
        {
            'id': plan['id'],
            'name': plan['nickname'],
            'amount': plan['amount'] / 100,
            'currency': plan['currency'],
            'interval': plan['interval'],
            'trial_days': plan['trial_period_days']
        }

        for plan in plans
    ]

    return plans


def get_subscription(subscription_id):

    subscription = stripe.Subscription.retrieve(subscription_id)

    trial_start = datetime.fromtimestamp(subscription['trial_start']).replace(tzinfo=timezone.utc) if isinstance(subscription['trial_start'], int) else None
    trial_end = datetime.fromtimestamp(subscription['trial_end']).replace(tzinfo=timezone.utc) if isinstance(subscription['trial_end'], int) else None

    return {
        'item_id': subscription['items']['data'][0]['id'],
        'plan_name': subscription['plan']['nickname'],
        'plan_id': subscription['plan']['id'],
        'status': subscription['status'],
        'trial_start': trial_start,
        'trial_end': trial_end
    }




def update_customer_payment_method(card_token, customer_id):
    # Whenever you attach a card to a customer, Stripe will automatically validate the card.
    try:
        return stripe.Customer.modify(customer_id, source=card_token)
    except stripe.error.CardError as e:
        err = e.json_body.get('error', {})
        return {
            'error': 'payment_error',
            'message': err.get('message')
        }


def update_subscription(subscription_id, plan_id, item_id, trial_end='now'):

    subscription = stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=False,
        items=[{
            'id': item_id,
            'plan': plan_id,
        }],
        trial_end=trial_end,
        expand = ['latest_invoice.payment_intent'],
    )

    subscription_status = subscription.status

    try: # immediate payment required
        is_paid = subscription.latest_invoice.payment_intent.charges.data[0].paid
        payment_status = subscription.latest_invoice.payment_intent.charges.data[0].status
        print('immediate payment required')

    except AttributeError: # immediate payment not required
        print('immediate payment not required')
        return {
            'id': subscription.id,
            'status': subscription_status
        }

    else:
        # past_due False failed
        print(subscription_status, is_paid, payment_status)

        if subscription_status in ['past_due', 'incomplete']:

            if payment_status in ['failed', 'requires_payment_method']:
                return {
                    'error': 'payment_error',
                    'message': 'There was an error charging your card. Please try again or use another card.'
                }

            elif payment_status == 'requires_action':
                return {
                    'error': 'payment_error',
                    'message': 'Additional action required.'
                }

            else:
                raise ValueError('unknown payment_status: ' + payment_status)

        elif subscription_status == 'active':
            return {
                'id': subscription.id,
                'status': subscription_status
            }

        else:
            raise ValueError('unknown subscription status: ' + subscription_status)














