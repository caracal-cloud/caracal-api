from corsheaders.defaults import default_methods, default_headers
import os
import stripe # imported in child settings

APPLICATION_NAME = 'Caracal'
APPLICATION_SHORT_NAME = 'caracal'

AGOL_CLIENT_ID = os.environ['CARACAL_AGOL_CLIENT_ID']
AGOL_CLIENT_SECRET = os.environ['CARACAL_AGOL_CLIENT_SECRET']

# tuma-admin
AWS_ACCESS_KEY_ID = os.environ['TUMA_AWS_KEY']
AWS_SECRET_ACCESS_KEY = os.environ['TUMA_AWS_SECRET']
AWS_REGION = "us-east-1"
DYNAMO_CONFIG_TABLE_NAME = 'caracal-global-configuration'

BILLING_CUSTOM_RECORDS_LIMIT_INDIV = 50000
BILLING_CUSTOM_RECORDS_LIMIT_TEAM = 500000
BILLING_DESTINATIONS_LIMIT_INDIV = -1 # unlimited
BILLING_DESTINATIONS_LIMIT_TEAM = -1
BILLING_SOURCE_LIMIT_INDIV = 10
BILLING_SOURCE_LIMIT_TEAM = -1

COLLARS_GET_DATA_RATE_MINUTES = 15
COLLARS_KML_PERIOD_HOURS = [24, 72, 168, 720]


DUMMY_EMAIL = 'dummy@caracal.cloud'
DUMMY_SHORT_NAME = 'dummy3141592'

DEFAULT_EMAIL_SENDER = "noreply@caracal.cloud"
DEFAULT_EMAIL_RECIPIENT = "contact@caracal.cloud"
OVERLORD_EMAIL = os.environ['CARACAL_OVERLORD_EMAIL']
OVERLORD_PASSWORD = os.environ['CARACAL_OVERLORD_PASSWORD']

S3_USER_CREDENTIALS_TABLE = 'caracal-user-access-credentials'

SRID = 4326 # Spatial Reference System Identifier - still using this over global config.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEBUG = True

SECRET_KEY = os.environ['CARACAL_SECRET']

INSTALLED_APPS = [
    'jet',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    'django_extensions',
    'rest_framework',
    'corsheaders',
    'drf_yasg',

    'account',
    'activity',
    'billing',
    'collars',
    'custom_source',
    'drives',
    'outputs',
    'public',
    'radios'
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

AUTH_USER_MODEL = 'account.Account'

ROOT_URLCONF = 'caracal.urls'

JWT_AUTH_HEADER_PREFIX = "JWT"

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,

    #'DEFAULT_THROTTLE_CLASSES': (
    #    'rest_framework.throttling.AnonRateThrottle',
    #    'rest_framework.throttling.UserRateThrottle'
    #),
    #'DEFAULT_THROTTLE_RATES': {
    #    'anon': '100/minute',
    #    'user': '200/minute'
    #}
}

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = default_methods # + ('NEW_ACTION',)
CORS_ALLOW_HEADERS = default_headers # + ('new-header',)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'JWT': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'DEFAULT_API_URL': 'https://api.caracal.cloud'
}


SHELL_PLUS_PRE_IMPORTS = (
    ('account.models', '*'),
    ('account.serializers', '*'),
    ('collars.models', '*'),
    ('collars.serializers', '*'),
    ('outputs.models', '*'),
    ('outputs.serializers', '*'),
    ('caracal.common.stripe_utils', '*')

)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR+'/caracal/templates', BASE_DIR+'/account/templates'],
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


JET_DEFAULT_THEME = 'light-gray'

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = '/static/'
