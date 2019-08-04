from caracal.settings.base import *

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

# fixme: change this
DEBUG = True
TESTING = True

STAGE = 'production'

COGNITO_USER_POOL_NAME = 'Caracal-Production'
COGNITO_USER_POOL_ID = os.environ['CARACAL_PROD_COGNITO_USERPOOL_ID']
COGNITO_APP_ID = os.environ['CARACAL_PROD_COGNITO_APP_ID']

GOOGLE_CLIENT_ID = os.environ['CARACAL_GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['CARACAL_GOOGLE_CLIENT_SECRET']

HOSTNAME = 'https://api.caracal.cloud'

S3_FILES_BUCKET = "caracal-user-prod"

ALLOWED_HOSTS = ['127.0.0.1', 'api.caracal.cloud', 'caracal-api-prod.yhhegxdi5a.us-east-1.elasticbeanstalk.com']

DATABASE_NAME = 'caracal_prod'
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
