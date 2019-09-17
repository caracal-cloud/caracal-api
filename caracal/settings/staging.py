from caracal.settings.base import *

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

DEBUG = True
TESTING = False

STAGE = 'staging'

COGNITO_USER_POOL_NAME = 'Caracal-Staging'
COGNITO_USER_POOL_ID = os.environ['CARACAL_STAGING_COGNITO_USERPOOL_ID']
COGNITO_APP_ID = os.environ['CARACAL_STAGING_COGNITO_APP_ID']

GOOGLE_CLIENT_ID = os.environ['CARACAL_DEV_GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['CARACAL_DEV_GOOGLE_CLIENT_SECRET']

HOSTNAME = 'https://api.staging.caracal.cloud'

S3_USER_DATA_BUCKET = "caracal-user-staging"

stripe.api_key = os.environ['CARACAL_TEST_STRIPE_API_KEY']

ALLOWED_HOSTS = ['127.0.0.1', 'api.staging.caracal.cloud'] # TODO: add EB

DATABASE_NAME = 'caracal_staging'
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': DATABASE_NAME,
        'USER': os.environ['CARACAL_PG_USER'],
        'PASSWORD': os.environ['CARACAL_PG_PASSWORD'],
        'HOST': os.environ['CARACAL_PG_HOST'],
        'PORT': '5432'
    },
    'OPTIONS': {
        'charset': 'utf8',
        'use_unicode': True,
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

"""
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': os.environ['CARACAL_MEMCACHED_LOCATION'], 
    }
}
"""

sentry_sdk.init(
    dsn="https://07c4110769a945c18d4395adf1bce4bd@sentry.io/1419868",
    integrations=[DjangoIntegration()]
)
ignore_logger("django.security.DisallowedHost")
