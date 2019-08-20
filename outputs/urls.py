from django.urls import path, include

from outputs import views

urlpatterns = [
    path('agol/', include([
        path('oauth/', include([
            path('get_request_url/', views.GetAgolOauthRequestUrlView.as_view()),
            path('response/', views.AgolOauthResponseView.as_view(), name='agol-oauth-response'),
        ])),
        path('get_account/', views.GetAgolAccountView.as_view())
    ]))

]
