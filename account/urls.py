
from django.conf import settings
from django.urls import include, path
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status

from account.views import password, profile, register, social_auth, tokens
from account import serializers


decorated_get_profile_view = \
   swagger_auto_schema(
       method='get',
       responses={status.HTTP_200_OK: serializers.GetProfileSerializer},
       operation_id='account - get profile',
       security=[settings.SWAGGER_SETTINGS['SECURITY_DEFINITIONS']],
   )(profile.GetProfileView.as_view())

urlpatterns = [
    #path('forced_password_reset/', password.ForcedPasswordResetView.as_view()),
    path('force_organization_update/', profile.ForceOrganizationUpdateView.as_view()),
    path('forgot_password/', password.ForgotPasswordView.as_view()),
    path('forgot_password_confirm/', password.ForgotPasswordConfirmView.as_view()),
    path('get_profile/', decorated_get_profile_view),
    path('login/', tokens.LoginView.as_view()),
    path('logout/', tokens.LogoutView.as_view()),
    path('refresh/', tokens.RefreshView.as_view()),
    path('register/', register.RegisterView.as_view()),
    path('social_auth/', include([
        path('google/', social_auth.GoogleAuthView.as_view()),
        path('test/', social_auth.TestSocialAuthView.as_view())
    ])),
    path('update_account/', profile.UpdateAccountView.as_view())
]
