from django.contrib import admin

from outputs.models import DataConnection, DataOutput


@admin.register(DataConnection)
class DataConnectionAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'realtime_account', 'realtime_alert', 'drive_account', 'output']
    search_fields = ['uid', 'output__type']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']


@admin.register(DataOutput)
class DataOutputAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'type', 'status']
    search_fields = ['uid', 'type', 'status']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']
