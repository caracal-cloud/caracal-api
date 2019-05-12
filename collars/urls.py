from django.urls import include, path

from collars import views

urlpatterns = [
    path('add_account/', views.AddCollarAccountView.as_view()),
    path('delete_account/', views.DeleteCollarAccountView.as_view()),
    path('get_accounts/', views.GetCollarAccountsView.as_view()),
    path('get_account/<str:uid>', views.GetCollarAccountDetailView.as_view(), name='collar-account-detail'),
    path('get_individuals/', views.GetCollarIndividualsView.as_view()),
    path('get_individual/<str:uid>', views.GetCollarIndividualDetailView.as_view(), name='collar-individual-detail'),
    path('update_account/', views.UpdateCollarAccountView.as_view()),
    path('update_individual/', views.UpdateCollarIndividualView.as_view()),
]
