from django.contrib import admin

from activity.models import ActivityAlert, ActivityChange


@admin.register(ActivityChange)
class ActivityChangeAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'message']
    search_fields = ['uid', 'message']
    list_filter = ['is_active']
    ordering = ['-datetime_created']

