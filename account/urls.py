from django.urls import include, path

from account.views import password, outputs, profile, register, tokens

urlpatterns = [
    path('forced_password_reset/', password.ForcedPasswordResetView.as_view()),
    path('forgot_password/', password.ForgotPasswordView.as_view()),
    path('forgot_password_confirm/', password.ForgotPasswordConfirmView.as_view()),
    path('get_profile/', profile.GetProfileView.as_view()),
    path('get_kmz_hrefs/', outputs.GetKmzHrefsView.as_view()),
    path('login/', tokens.LoginView.as_view()),
    path('logout/', tokens.LogoutView.as_view()),
    path('refresh/', tokens.RefreshView.as_view()),
    path('register/', register.RegisterView.as_view()),
    path('update_account/', profile.UpdateAccountView.as_view()),
    path('update_organization/', profile.UpdateOrganizationView.as_view()),
]
