from django.urls import path, include

from outputs import views

urlpatterns = [
    path('agol/', include([
        path('oauth/', include([
            path('get_request_url/', views.GetAgolOauthRequestUrlView.as_view()),
            path('response/', views.AgolOauthResponseView.as_view(), name='agol-oauth-response'),
        ])),
        # path('add_account/', views.AddAgolAccountView.as_view())
    ]))

]
