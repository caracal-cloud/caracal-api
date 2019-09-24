from django.contrib import admin

from custom_source.models import Record, Source


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'datetime_recorded', 'source', 'device_id', 'position']
    search_fields = ['uid', 'source__name']
    list_filter = []
    ordering = ['-datetime_recorded']
    readonly_fields = ['datetime_created', 'alt_m', 'device_id', 'speed_kmh', 'temp_c']


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'name', 'description']
    search_fields = ['uid', 'name', 'organization__name']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated', 'write_key']


