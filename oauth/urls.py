from django.urls import path

from oauth import views

urlpatterns = [
    path('agol/', views.AgolOauthView.as_view()),
    path('google/', views.GoogleOauthView.as_view())
]