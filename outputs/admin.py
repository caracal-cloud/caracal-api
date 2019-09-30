from django.contrib import admin

from outputs.models import AgolAccount, DataConnection


@admin.register(AgolAccount)
class AgolAccountAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'account', 'username']
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted',
                       'datetime_updated', 'feature_service_url', 'group_id']


@admin.register(DataConnection)
class DataConnectionAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'custom_source', 'drive_account', 'realtime_account',
                    'agol_account']
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']

