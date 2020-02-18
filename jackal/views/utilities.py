
from django.db.utils import IntegrityError
from jackal.models import Phone


def get_or_create_phone(device_id, network):
    try:
        return Phone.objects.get(device_id=device_id, network=network)
    except Phone.DoesNotExist:
        try:
            return Phone.objects.create(device_id=device_id, network=network)
        except IntegrityError:
            return Phone.objects.get(device_id=device_id, network=network)

