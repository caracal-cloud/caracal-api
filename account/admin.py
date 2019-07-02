from django.contrib import admin

from account.models import Account, Organization
from caracal.common.models import RealTimeAccount, RealTimeIndividual, RealTimePosition, RealTimePositionHash

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['uid', 'email', 'organization', 'name',
                    'phone_number', 'datetime_created']
    search_fields = ['uid', 'email', 'organization__name']
    list_filter = ['is_active', 'is_superuser', 'is_staff', 'is_admin']
    ordering = ['-datetime_created']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'timezone', 'datetime_created']
    search_fields = ['uid', 'name', 'short_name']
    list_filter = ['is_active']
    ordering = ['name']


@admin.register(RealTimeAccount)
class RealTimeAccountAdmin(admin.ModelAdmin):
    list_display = ['datetime_created', 'status', 'collar_account'] # add other children
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted']


@admin.register(RealTimeIndividual)
class RealTimeIndividualAdmin(admin.ModelAdmin):
    list_display = ['datetime_created', 'account', 'collar_individual'] # add other children
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted',
                       'last_position', 'datetime_last_position']


@admin.register(RealTimePosition)
class RealTimePositionAdmin(admin.ModelAdmin):
    list_display = ['datetime_created', 'account', 'individual',
                    'position', 'datetime_recorded',
                    'orbcomm_collar_position', 'savannah_tracking_collar_position'] # add other children
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted',
                       'position', 'datetime_recorded', 'temp_celcius']


@admin.register(RealTimePositionHash)
class RealTimePositionHashAdmin(admin.ModelAdmin):
    list_display = ['datetime_created', 'hash', 'account']
    search_fields = []
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'hash']

