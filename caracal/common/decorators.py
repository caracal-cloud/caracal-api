
from functools import wraps
from rest_framework import status
from rest_framework.response import Response

from caracal.common.models import get_num_sources


def check_source_limit(f):
    'docs'

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