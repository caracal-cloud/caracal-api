
from django.urls import path, include

from drives import views

urlpatterns = [
    path('google/', include([
        path('add_account/', views.AddDriveFileAccountView.as_view()),
        path('delete_account/', views.DeleteDriveFileAccountView.as_view()),

        path('get_accounts/', views.GetDriveFileAccountsView.as_view()),

        path('get_files/', views.GetGoogleDriveFilesView.as_view()),
        path('get_spreadsheet_sheets/', views.GetGoogleSpreadsheetSheetsView.as_view()),
        path('oauth/', include([
            path('get_request_url/', views.GetGoogleOauthRequestUrlView.as_view()),
            path('response/', views.GoogleOauthResponseView.as_view()),
        ])),
    ]))

]
