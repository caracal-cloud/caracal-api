from django.urls import path, include

from drives import views

urlpatterns = [
    path('google/', include([
        path('add_account/', views.AddGoogleAccountView.as_view()),
        path('get_documents/', views.GetGoogleDocumentsView.as_view()),
        path('get_document_sheets/', views.GetGoogleDocumentSheetsView.as_view()),
        path('oauth/', include([
            path('get_request_url/', views.GetGoogleOauthRequestUrlView.as_view()),
            path('response/', views.GoogleOauthResponseView.as_view()),
        ])),
    ]))

]
