from django.urls import path, include

from drives import views

urlpatterns = [
    path('google/', include([
        path('add_spreadsheet_account/', views.AddGoogleSpreadsheetView.as_view()),
        path('get_spreadsheets/', views.GetGoogleSpreadsheetsView.as_view()),
        path('get_spreadsheet_sheets/', views.GetGoogleSpreadsheetSheetsView.as_view()),
        path('oauth/', include([
            path('get_request_url/', views.GetGoogleOauthRequestUrlView.as_view()),
            path('response/', views.GoogleOauthResponseView.as_view()),
        ])),
    ]))

]
