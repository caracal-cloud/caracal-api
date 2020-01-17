
from functools import wraps
from rest_framework import status
from rest_framework.response import Response

from caracal.common.agol import is_account_connected
from caracal.common.models import get_num_sources
from outputs.models import AgolAccount


def check_source_limit(f):
    'Checks if the user has exceeded the source limit.'

    @wraps(f)
    def wrapper(view, request, *args, **kwargs):

        user = request.user
        organization = user.organization

        num_sources = get_num_sources(organization) # unlimited source_limit is -1
        
        if 0 < organization.source_limit <= num_sources:
            return Response({
                'error': 'source_limit_reached',
                'message': 'You have reached the limit of your plan. Consider upgrading for unlimited sources.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return f(view, request, *args, **kwargs)
    
    return wrapper


def check_agol_account_connected(f):
    'Check if the request indicates output_agol and checks if AGOL account exists.'

    @wraps(f)
    def wrapper(view, request, *args, **kwargs):

        data = request.data
        user = request.user

        if data.get('output_agol', False):
            try:
                agol_account = user.agol_account
            except AgolAccount.DoesNotExist:
                return Response({
                    'error': 'agol_account_required',
                    'message': 'ArcGIS Online account required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not is_account_connected(agol_account):
                return Response({
                    'error': 'refresh_token_invalid',
                    'message': 'Cannot refresh token. Remove ArcGIS account and reconnect.'
                }, status=status.HTTP_400_BAD_REQUEST)


        return f(view, request, *args, **kwargs)
    
    return wrapper




    