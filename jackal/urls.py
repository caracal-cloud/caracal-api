from django.urls import include, path

from jackal import views

urlpatterns = [

    path('add_call/', views.AddCallView.as_view()),
    path('add_contact/', views.AddContactView.as_view()),
    path('add_location/', views.AddLocationView.as_view()),
    path('add_text/', views.AddTextView.as_view()),
    path('create_network/', views.CreateNetworkView.as_view()),
    path('get_phones/', views.GetPhonesView.as_view()),
    path('get_phone/<str:uid>', views.GetPhoneDetailView.as_view(), name='phone-detail'),
    path('update_phone/', views.UpdatePhoneView.as_view())

]