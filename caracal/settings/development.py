from caracal.settings.base import *

DEBUG = True
TESTING = True

STAGE = 'development'

ALLOWED_HOSTS = ['*']

COGNITO_USER_POOL_NAME = 'Caracal-Development'
COGNITO_USER_POOL_ID = os.environ['CARACAL_DEV_COGNITO_USERPOOL_ID']
COGNITO_APP_ID = os.environ['CARACAL_DEV_COGNITO_APP_ID']

GOOGLE_CLIENT_ID = os.environ['CARACAL_DEV_GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['CARACAL_DEV_GOOGLE_CLIENT_SECRET']

HOSTNAME = 'http://localhost:8000'

S3_USER_DATA_BUCKET = "caracal-users-dev"

stripe.api_key = os.environ['CARACAL_TEST_STRIPE_API_KEY']

DATABASE_NAME = 'caracal_dev'
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': DATABASE_NAME,
        'USER': os.environ['LOCAL_PG_USER'],
        'PASSWORD': os.environ['LOCAL_PG_PASSWORD'],
        'HOST': os.environ['LOCAL_PG_HOST'],
        'PORT': '5433' # different port than deployed versions 
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