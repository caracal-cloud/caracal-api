from django.contrib import admin

from activity.models import ActivityAlert, ActivityChange


@admin.register(ActivityAlert)
class ActivityAlertAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'message', 'level']
    search_fields = ['uid', 'message', 'level']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']



@admin.register(ActivityChange)
class ActivityChangeAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'message']
    search_fields = ['uid', 'message']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created']

