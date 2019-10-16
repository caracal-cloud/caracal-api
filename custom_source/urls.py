from django.urls import include, path

from custom_source import views

urlpatterns = [

    path('add_record/', views.AddRecordView.as_view()),
    path('add_source/', views.AddSourceView.as_view()),
    path('delete_source/', views.DeleteSourceView.as_view()),
    path('get_devices/', views.GetDevicesView.as_view()),
    path('get_device/<str:uid>', views.GetDeviceDetailView.as_view(), name='device-detail'),
    path('get_sources/', views.GetSourcesView.as_view()),
    path('get_source/<str:uid>', views.GetSourceDetailView.as_view(), name='source-detail'),
    path('update_device/', views.UpdateDeviceView.as_view()),
    path('update_source/', views.UpdateSourceView.as_view())

]