

from collars.models import CollarProvider

def add_collar_providers():
    collar_providers = [
        {
            'name': 'Savannah Tracker',
            'short_name': 'savannah',
            'base_url': 'http://52.72.63.142/savannah_data/',
            'is_available': True
        },
        {
            'name': 'Orbcomm / Skygistics',
            'short_name': 'orbcomm',
            'base_url': 'http://skyq3.skygistics.com/TrackingAPI.asmx/',
            'is_available': True
        }
    ]

    for provider in collar_providers:
        CollarProvider.objects.create(**provider)
