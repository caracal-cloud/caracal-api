from django.contrib import admin

from account.models import Account, AlertRecipient, Organization
from caracal.common.models import RealTimeAccount, RealTimeIndividual, RealTimePosition, RealTimePositionHash


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['uid_cognito', 'email', 'organization', 'name',
                    'phone_number', 'registration_method', 'datetime_created']
    search_fields = ['uid_cognito', 'uid_google', 'email', 'organization__name']
    list_filter = ['is_active', 'is_superuser', 'is_staff', 'is_admin']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated', 
                       'custom_access_jwt_id', 'custom_refresh_jwt_id', 
                       'temp_google_oauth_access_token', 'temp_google_oauth_access_token_expiry',
                       'temp_google_oauth_refresh_token', 'password']


@admin.register(AlertRecipient)
class AlertRecipientAdmin(admin.ModelAdmin):
    list_display = ['uid', 'email', 'phone_number', 'datetime_created']
    search_fields = ['uid', 'email', 'phone_number']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['uid', 'name', 'short_name', 'timezone', 'datetime_created']
    search_fields = ['uid', 'name', 'short_name']
    list_filter = ['is_active', 'update_required']
    ordering = ['name']
    readonly_fields = ['datetime_created', 'datetime_deleted', 'datetime_updated']


@admin.register(RealTimeAccount)
class RealTimeAccountAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'title', 'status', 'source', 'provider', 'type']
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted']


@admin.register(RealTimeIndividual)
class RealTimeIndividualAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'account', 'device_id', 'status', 'name', 'subtype']
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted']


@admin.register(RealTimePosition)
class RealTimePositionAdmin(admin.ModelAdmin):
    list_display = ['uid', 'datetime_created', 'account', 'individual',
                    'position', 'datetime_recorded']
    search_fields = ['uid']
    list_filter = ['is_active']
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'datetime_updated', 'datetime_deleted',
                       'datetime_recorded', 'temp_c']


@admin.register(RealTimePositionHash)
class RealTimePositionHashAdmin(admin.ModelAdmin):
    list_display = ['hash', 'datetime_created', 'account', 'individual']
    search_fields = ['account__source', 'account__provider', 'individual__device_id']
    list_filter = []
    ordering = ['-datetime_created']
    readonly_fields = ['datetime_created', 'hash']

