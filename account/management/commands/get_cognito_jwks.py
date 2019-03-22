
from django.conf import settings
from django.core.management.base import BaseCommand
import json
import os
import requests


class Command(BaseCommand):
    help = 'Initializes the all JWKs from all user pools in Cognito.'

    def handle(self, *args, **options):
        user_pool_envar_names = ['CARACAL_TEST_COGNITO_USERPOOL_ID',
                                 'CARACAL_DEV_COGNITO_USERPOOL_ID',
                                 'CARACAL_STAGING_COGNITO_USERPOOL_ID',
                                 'CARACAL_PROD_COGNITO_USERPOOL_ID']

        jwk_data = {"keys": list()}
        for pool_id_envar in user_pool_envar_names:
            try:
                jwks_url = "https://cognito-idp.%s.amazonaws.com/%s/.well-known/jwks.json" % \
                           (settings.AWS_REGION, os.environ[pool_id_envar])
                res = requests.get(jwks_url)
                res = res.json()

                for jwk in res.get('keys', list()):
                    jwk_data['keys'].append(jwk)

            except Exception as e:
                print("Skipping: " + pool_id_envar)
                continue

        with open(os.path.join(os.getcwd(), 'account', 'resources', 'jwks.json'), 'w') as f:
            f.write(json.dumps(jwk_data, indent=4, sort_keys=True))
