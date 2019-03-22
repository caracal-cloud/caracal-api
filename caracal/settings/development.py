from caracal.settings.base import *

DEBUG = True
TESTING = True

ALLOWED_HOSTS = ['*']

COGNITO_USER_POOL_ID = os.environ['CARACAL_DEV_COGNITO_USERPOOL_ID']
COGNITO_APP_ID = os.environ['CARACAL_DEV_COGNITO_APP_ID']
S3_FILES_BUCKET = "caracal-user-development"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'development.db'
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}