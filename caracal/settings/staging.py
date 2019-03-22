from caracal.settings.base import *

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DEBUG = True
TESTING = False

COGNITO_USER_POOL_ID = os.environ['CARACAL_STAGING_COGNITO_USERPOOL_ID']
COGNITO_APP_ID = os.environ['CARACAL_STAGING_COGNITO_APP_ID']
S3_FILES_BUCKET = "caracal-user-staging"

ALLOWED_HOSTS = ['127.0.0.1', 'api.staging.caracal.cloud'] # TODO: add EB

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'staging.db'
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