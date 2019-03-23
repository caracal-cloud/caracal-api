from django.urls import include, path

from collars import views

urlpatterns = [
    path('add/', views.AddCollarView.as_view()),
]
