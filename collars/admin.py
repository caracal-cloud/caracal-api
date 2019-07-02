from django.contrib import admin

from django.contrib import admin

from collars.models import CollarProvider, CollarAccount, CollarIndividual


@admin.register(CollarProvider)
class CollarProviderAdmin(admin.ModelAdmin):
    list_display = ['uid', 'name', 'short_name', 'base_url', 'datetime_created']
    search_fields = ['name', 'short_name']
    list_filter = ['is_active', 'is_available']
    ordering = ['name']


@admin.register(CollarAccount)
class CollarAccountAdmin(admin.ModelAdmin):
    list_display = ['collar_account_uid', 'account_ptr_id', 'organization',
                    'provider', 'status', 'species', 'title']
    search_fields = ['species', 'title']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted']


@admin.register(CollarIndividual)
class CollarIndividualAdmin(admin.ModelAdmin):
    list_display = ['uid', 'individual_ptr_id',
                    'collar_account', 'device_id',
                    'name', 'sex', 'subtype', 'status']
    search_fields = ['name', 'sex', 'subtype', 'status']
    list_filter = ['is_active', 'sex', 'subtype', 'status']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted',
                       'last_position', 'datetime_last_position', 'monthly_paths']
