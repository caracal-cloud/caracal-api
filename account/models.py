from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import django.db.models as m
from django.utils import timezone
from sentry_sdk import capture_message
import uuid

from auth import cognito


class Organization(m.Model):
    uid = m.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    datetime_created = m.DateTimeField(default=timezone.now)
    datetime_updated = m.DateTimeField(null=True)
    datetime_deleted = m.DateTimeField(null=True)
    is_active = m.BooleanField(default=True) # alias for deleted

    name = m.CharField(max_length=150, blank=False, null=False)
    short_name = m.CharField(max_length=20, blank=False, null=False, unique=True)
    timezone = m.CharField(max_length=50, default='Africa/Kigali')
    logo_object_key = m.CharField(max_length=255, null=True)

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
            user.uid = sub
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
        user.set_password(password)
        user.save(using=self._db)
        return user


def jwt_get_secret_key(user):
    return user.jwt_secret


class Account(AbstractBaseUser, PermissionsMixin):
    uid = m.UUIDField(unique=True, editable=False, default=uuid.uuid4)
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
    is_admin = m.BooleanField(default=False) # is this the organization-admin?

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return "%s - %s" % (self.name, self.email)

    class Meta:
        ordering = ['email']
        verbose_name = 'account'
        verbose_name_plural = 'accounts'


























