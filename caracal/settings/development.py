from caracal.settings.base import *

DEBUG = True
TESTING = True

ALLOWED_HOSTS = ['*']

COGNITO_USER_POOL_ID = os.environ['CARACAL_DEV_COGNITO_USERPOOL_ID']
COGNITO_APP_ID = os.environ['CARACAL_DEV_COGNITO_APP_ID']
S3_FILES_BUCKET = "caracal-user-development"

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',
        'NAME': 'caracal_dev',
        'USER': os.environ['LOCAL_MYSQL_USER'],
        'PASSWORD': os.environ['LOCAL_MYSQL_PASSWORD'],
        'HOST': os.environ['LOCAL_MYSQL_HOST'],
        'PORT': '3306',
    },
    'OPTIONS': {
        'charset': 'utf8mb4',
        'use_unicode': True,
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}