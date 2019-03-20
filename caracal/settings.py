
from corsheaders.defaults import default_methods, default_headers
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
import urllib

# tuma-admin
AWS_ACCESS_KEY_ID = os.environ['TUMA_AWS_KEY']
AWS_SECRET_ACCESS_KEY = os.environ['TUMA_AWS_SECRET']
AWS_REGION = "us-east-1"

# Celery
BROKER_URL = 'sqs://{0}:{1}@'.format(
    urllib.parse.quote(AWS_ACCESS_KEY_ID, safe=''),
    urllib.parse.quote(AWS_SECRET_ACCESS_KEY, safe='')
)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_DEFAULT_QUEUE = 'caracal.fifo'
CELERY_RESULT_BACKEND = None # Disabling the results backend
BROKER_TRANSPORT_OPTIONS = {
    'region': 'us-east-1',
    'polling_interval': 20,
}

DEFAULT_EMAIL_RECIPIENT = "casey@caracal.cloud"

sentry_sdk.init(
    dsn="https://07c4110769a945c18d4395adf1bce4bd@sentry.io/1419868",
    integrations=[DjangoIntegration()]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECRET_KEY = 'e3dk1qlemm9$ptb**v-jfasa_)8c)lc4!^2^0&znctzdg&x-fu'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'api.caracal.cloud', 'caracal-api-prod.yhhegxdi5a.us-east-1.elasticbeanstalk.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'rest_framework',
    'corsheaders',
    'drf_yasg',
    'public'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # order is important!
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'caracal.urls'

JWT_AUTH_HEADER_PREFIX = "JWT"

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/minute',
        'user': '200/minute'
    }
}

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = default_methods # + ('NEW_ACTION',)
CORS_ALLOW_HEADERS = default_headers # + ('new-header',)

SHELL_PLUS_PRE_IMPORTS = (

)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'caracal.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = '/static/'
