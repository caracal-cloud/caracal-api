
from functools import wraps
from rest_framework import status
from rest_framework.response import Response

from jackal.models import Network, Phone


def check_network_exists(f):
    "Checks that the network identified by the write key exists."

    @wraps(f)
    def wrapper(view, request, *args, **kwargs):

        data = request.data
        user = request.user

        write_key = data['write_key']

        try:
            network = Network.objects.get(write_key=write_key, is_active=True)
        except Network.DoesNotExist:
            return Response({
                'error': 'network_does_not_exist',
                'message': 'Network does not exist.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return f(view, request, *args, **kwargs)
    
    return wrapper

    