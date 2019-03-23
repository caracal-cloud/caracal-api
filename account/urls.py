from django.urls import include, path

from account.views import password, register, tokens

urlpatterns = [
    path('forced_password_reset/', password.ForcedPasswordResetView.as_view()),
    path('forgot_password/', password.ForgotPasswordView.as_view()),
    path('forgot_password_confirm/', password.ConfirmForgotPasswordView.as_view()),
    path('login/', tokens.LoginView.as_view()),
    path('refresh/', tokens.RefreshView.as_view()),
    path('register/', register.RegisterView.as_view()),
]
