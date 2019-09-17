from django.urls import include, path

from activity import views

urlpatterns = [
    # Stripe webhooks
    path('stripe/', include([
        # path('subscription_updated/', None)

    ]))
]
