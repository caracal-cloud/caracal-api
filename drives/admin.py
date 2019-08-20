from django.contrib import admin

from drives.models import DriveFileAccount


@admin.register(DriveFileAccount)
class DriveFileAccountAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'provider', 'title',
                    'file_type', 'coordinate_system']
    search_fields = ['uid', 'message', 'level']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']


