from django.urls import include, path

from activity import views

urlpatterns = [
    path('get_alerts/', views.GetAlertsView.as_view()),
    path('get_changes/', views.GetChangesView.as_view()),
    path('get_overview_metrics/', views.GetOverviewMetricsView.as_view())
]
