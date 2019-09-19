from django.urls import include, path

from billing import views

urlpatterns = [

    path('get_plans/', views.GetPlansView.as_view()),

    path('stripe_webhook/', views.StripeWebhookView.as_view()),

    path('update_payment_method/', views.UpdatePaymentMethodView.as_view()),

    path('update_paid_subscription/', views.UpdatePaidSubscriptionView.as_view()),
    path('update_trial_to_paid_subscription/', views.UpdateTrialToPaidSubscriptionView.as_view()),

]
