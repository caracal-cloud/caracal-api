from django.urls import path

from radios import views

urlpatterns = [
    path('add_account/', views.AddAccountView.as_view()),
    path('add_position/', views.AddPositionView.as_view()),
    path('delete_account/', views.DeleteAccountView.as_view()),
    path('get_accounts/', views.GetAccountsView.as_view()),
    path('get_account/<str:uid>', views.GetRadioAccountDetailView.as_view(), name='radio-account-detail'),
    path('get_individuals/', views.GetRadioIndividualsView.as_view()),
    path('get_individual/<str:uid>', views.GetRadioIndividualDetailView.as_view(), name='radio-individual-detail'),
    path('update_account/', views.UpdateRadioAccountView.as_view()),
    path('update_individual/', views.UpdateRadioIndividualView.as_view()),
]
