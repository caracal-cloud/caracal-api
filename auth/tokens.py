

import datetime
from django.conf import settings
import jwt
import uuid

issuer = 'caracal.cloud'


def generate_access_token(uid_cognito):
    jti = str(uuid.uuid4())
    return jwt.encode({
        'iss': issuer,
        'sub': uid_cognito,
        'jti': jti,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, settings.SECRET_KEY, algorithm='HS256'), jti


def generate_refresh_token(uid_cognito):
    jti = str(uuid.uuid4())
    return jwt.encode({
        'iss': issuer,
        'sub': uid_cognito,
        'jti': jti,
        # 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=10000)
    }, settings.SECRET_KEY, algorithm='HS256'), jti