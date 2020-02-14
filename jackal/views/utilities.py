
from jackal.models import Phone


def get_or_create_phone(device_id, network):
    try:
        return Phone.objects.get(device_id=device_id, network=network, is_active=True)
    except Phone.DoesNotExist:
        return Phone.objects.create(device_id=device_id, network=network)
