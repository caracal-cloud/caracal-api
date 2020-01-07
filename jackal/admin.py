from django.contrib import admin

from jackal.models import Call, Contact, Location, Network, OtherPhone, Phone, Text



@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'datetime_recorded', 'phone', 'other_phone', 'network', 'duration_secs']
    search_fields = ['other_phone__phone_number', 'other_phone__name']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'phone', 'other_phone', 'network']
    search_fields = ['other_phone__name', 'other_phone__phone_number']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'datetime_recorded', 'phone', 'network', 'position', 'accuracy_m']
    search_fields = []
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'datetime_recorded', 'phone', 'other_phone', 'network', 'message']
    search_fields = ['other_phone__name', 'other_phone__phone_number', 'message']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_recorded']


@admin.register(OtherPhone)
class OtherPhoneAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'network', 'name', 'phone_number']
    search_fields = ['uid', 'name', 'phone_number', 'description', 'mark']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']


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

