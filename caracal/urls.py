
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="Caracal API",
      default_version='v1',
      description="Caracal API Documentation",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('account/', include('account.urls')),
    path('activity/', include('activity.urls')),
    path('billing/', include('billing.urls')),
    re_path(r'^jet/', include('jet.urls', 'jet')),
    path('cybersyn1971/', admin.site.urls),
    path('collars/', include('collars.urls')),
    path('drives/', include('drives.urls')),
    path('outputs/', include('outputs.urls')),
    path('public/', include('public.urls')),
    path('radios/', include('radios.urls')),
    re_path(r'^$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]