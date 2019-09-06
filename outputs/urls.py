from django.urls import path, include

from outputs.views import agol, kmz

# TODO: logout of agol

urlpatterns = [
    path('agol/', include([
        path('disconnect/', agol.DisconnectAgolView.as_view()),
        path('get_account/', agol.GetAgolAccountView.as_view()),
        # TODO: figure out how this plays with demo
        path('oauth/', include([
            path('get_request_url/', agol.GetAgolOauthRequestUrlView.as_view()),
            path('response/', agol.AgolOauthResponseView.as_view(), name='agol-oauth-response'),
        ])),
    ])),

    path('get_kmz_hrefs/', kmz.GetKmzHrefsView.as_view())

]
