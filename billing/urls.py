from django.urls import include, path

from billing import views

urlpatterns = [

    path('get_plans/', views.GetPlansView.as_view()),

    path('stripe_webhook/', views.StripeWebhookView.as_view()),

    # update payment method if past due
    path('update_payment_method/', views.UpdatePaymentMethodView.as_view()),

    # update plan if not trialing
    path('update_plan/', views.UpdatePaidSubscriptionView.as_view()),

    # upgrade from trial account, reactivate account trial expired, reactivate account after canceled
    path('update_plan_and_payment_method/', views.UpdatePlanAndPaymentMethodView.as_view()),

]
