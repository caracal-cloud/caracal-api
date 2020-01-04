
from django.conf import settings
from django.urls import include, path
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status

from account.views import alerts, password, profile, register, social_auth, tokens
from account import serializers


decorated_get_profile_view = \
   swagger_auto_schema(
       method='get',
       responses={status.HTTP_200_OK: serializers.GetProfileSerializer},
       operation_id='account - get profile',
       security=[settings.SWAGGER_SETTINGS['SECURITY_DEFINITIONS']],
   )(profile.GetProfileView.as_view())

urlpatterns = [
    path('alerts/', include([
        path('add_recipient/', alerts.AddRecipientView.as_view()),
        path('delete_recipient/', alerts.DeleteRecipientView.as_view()),
        path('get_recipients/', alerts.GetRecipientsView.as_view()),
    ])),
    #path('forced_password_reset/', password.ForcedPasswordResetView.as_view()),
    path('force_organization_update/', profile.ForceOrganizationUpdateView.as_view()), # okay, is this being used?
    path('forgot_password/', password.ForgotPasswordView.as_view()),
    path('forgot_password_confirm/', password.ForgotPasswordConfirmView.as_view()), # okay
    path('get_profile/', decorated_get_profile_view), # okay
    path('get_account_status/', profile.GetAccountStatusView.as_view()), # okay, later remove stripe...
    path('login/', tokens.LoginView.as_view()), # okay
    path('logout/', tokens.LogoutView.as_view()), # okay
    path('refresh/', tokens.RefreshView.as_view()), # okay
    path('register/', register.RegisterView.as_view()), # okay
    path('social_auth/', include([
        path('google/', social_auth.GoogleAuthView.as_view()), # okay
        path('test/', social_auth.TestSocialAuthView.as_view()) # okay
    ])),
    path('update_account/', profile.UpdateAccountView.as_view()) # okay
]
