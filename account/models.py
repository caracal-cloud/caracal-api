
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import django.db.models as m
from django.utils import timezone
from sentry_sdk import capture_message
import uuid

from auth import cognito
from caracal.common import constants
from caracal.common.aws_utils.cognito import create_user, confirm_account


class Organization(m.Model):

    # fixme: clean up circular import when using BaseAsset
    uid = m.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = m.DateTimeField(default=timezone.now)
    datetime_updated = m.DateTimeField(null=True)
    datetime_deleted = m.DateTimeField(null=True)
    is_active = m.BooleanField(default=True)

    name = m.CharField(max_length=150, blank=False, null=True)
    short_name = m.CharField(max_length=50, blank=False, null=False, unique=True)
    timezone = m.CharField(max_length=50, default='Africa/Kigali')
    logo_object_key = m.CharField(max_length=255, blank=True, null=True)

    # billing
    custom_records_limit = m.IntegerField(default=settings.BILLING_CUSTOM_RECORDS_LIMIT_INDIV)
    destinations_limit = m.IntegerField(default=settings.BILLING_DESTINATIONS_LIMIT_INDIV)
    source_limit = m.IntegerField(default=settings.BILLING_SOURCE_LIMIT_INDIV)
    is_trialing = m.BooleanField(default=True) # is currently trialing, or expired trial account
    stripe_customer_id = m.CharField(max_length=100, blank=True, null=True)
    stripe_plan_id = m.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = m.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_status = m.CharField(max_length=100, blank=True, null=True)

    update_required = m.BooleanField(default=False, null=True) # organization update required to complete registration

    class Meta:
        ordering = ['name']

    def __str__(self):
        return "%s" % (self.name)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, cognito_idp_client, **extra_fields):
        """
        Creates and saves a User to Cognito and Django DB backend
        """
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)

        try:
            sub = cognito.register(email, password, cognito_idp_client)
            user.uid_cognito = sub
            user.save(using=self._db)
            return user

        except cognito_idp_client.exceptions.InvalidParameterException:
            capture_message("cognito_invalid_parameter: verify user pool has domain or valid email", level="error")
            return None

    def create_user(self, email, password, cognito_idp_client, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, cognito_idp_client, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):

        try: # we can only have 1 superuser
            Account.objects.get(is_superuser=True)
            print('superuser already exists')
            return
        except Account.DoesNotExist:
            pass

        try:
            org = Organization.objects.get(short_name=settings.APPLICATION_SHORT_NAME)
        except Organization.DoesNotExist:
            org = Organization.objects.create(name=settings.APPLICATION_NAME, short_name=settings.APPLICATION_SHORT_NAME)

        extra_fields.setdefault('organization', org)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)

        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)

        # create superuser in Cognito, will use Cognito auth later with admin dashboard
        sub = create_user(email, password, registration_method="superuser")

        user.uid_cognito = sub
        user.set_password(password)
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser, PermissionsMixin):

    uid_cognito = m.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    uid_google = m.CharField(max_length=100, editable=False, null=True)

    datetime_created = m.DateTimeField(default=timezone.now)
    datetime_updated = m.DateTimeField(null=True)
    datetime_deleted = m.DateTimeField(null=True)
    is_active = m.BooleanField(default=True)

    organization = m.ForeignKey(Organization, on_delete=m.CASCADE, related_name="accounts")
    email = m.EmailField(unique=True, max_length=150) # real make is 191 for utf8mb4
    name = m.CharField(max_length=150)
    phone_number = m.CharField(max_length=50, blank=True, null=True)

    is_superuser = m.BooleanField(default=False) # project-wide superuser
    is_staff = m.BooleanField(default=False) # super user or agent
    is_admin = m.BooleanField(default=False) # is this the organization-admin

    registration_method = m.CharField(max_length=50, choices=constants.REGISTRATION_METHODS, default='email', null=True)
    custom_access_jwt_id = m.UUIDField(null=True)
    custom_refresh_jwt_id = m.UUIDField(null=True)

    # Temp Google tokens
    temp_google_oauth_access_token = m.TextField(null=True)
    temp_google_oauth_access_token_expiry = m.DateTimeField(null=True) # UTC
    temp_google_oauth_refresh_token = m.TextField(null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return "%s - %s" % (self.name, self.email)

    class Meta:
        ordering = ['email']
        verbose_name = 'account'
        verbose_name_plural = 'accounts'


























