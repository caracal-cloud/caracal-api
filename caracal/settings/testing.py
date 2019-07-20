from caracal.settings.base import *

DEBUG = False
TESTING = True

ALLOWED_HOSTS = ['*']

COGNITO_USER_POOL_ID = os.environ['CARACAL_TEST_COGNITO_USERPOOL_ID']
COGNITO_APP_ID = os.environ['CARACAL_TEST_COGNITO_APP_ID']

GOOGLE_CLIENT_ID = os.environ['CARACAL_DEV_GOOGLE_CLIENT_ID']

S3_FILES_BUCKET = "caracal-user-testing"

LOGIN_ENDPOINT = '/account/login/'
LOGOUT_ENDPOINT = '/account/logout/'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'testing.db'
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}