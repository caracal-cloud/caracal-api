from django.contrib import admin

from jackal.models import Call, Contact, Location, Network, Phone, Text



@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'phone', 'network', 'other_phone_number', 'duration_secs']
    search_fields = ['other_phone_number']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'phone', 'network', 'name', 'phone_number']
    search_fields = ['name', 'phone_number']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'phone', 'network', 'position', 'accuracy_m']
    search_fields = []
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'phone', 'network', 'other_phone_number', 'message']
    search_fields = ['other_phone_number', 'message']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'network', 'device_id', 'name', 'status']
    search_fields = ['uid', 'name', 'description', 'mark', 'phone_numbers', 'status']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated', 'device_id']


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'organization', 'write_key']
    search_fields = ['uid', 'organization__name', 'organization__short_name']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated', 'write_key']

