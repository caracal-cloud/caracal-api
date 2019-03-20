from django.urls import include, path

from public import views

urlpatterns = [
    path('contact/', views.ContactView.as_view()),
]
