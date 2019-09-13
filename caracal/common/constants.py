

ACCOUNT_STATUSES = [('healthy', 'healthy'), ('unhealthy', 'unhealthy'), ('pending', 'pending')]

# ALERT_FEEDBACK = [('confirm', 'confirm'), ('deny', 'deny')]
ALERT_LEVELS = [('low', 'low'), ('medium', 'medium'), ('high', 'high')]

BLOOD_TYPES = [('AB+', 'AB+')]

RT_ACCOUNT_PROVIDERS = [('orbcomm', 'orbcomm'), ('savannah_tracking', 'savannah_tracking'), ('trbonet', 'trbonet')]

COORDINATE_SYSTEMS = [('dd', 'dd'), # decimal degrees
                      ('dms', 'dms'), # degrees minutes seconds
                      ('utm', 'utm')] # universal transverse mercator

DEFAULT_IMAGE_FORMAT = 'png'

DRIVE_PROVIDERS = [('google', 'google')] # microsoft
DRIVE_FILETYPES = [('google_sheet', 'google_sheet'), ('excel', 'excel'), ('csv', 'csv'), ('geojson', 'geojson')]
DRIVE_PROVIDER_FILETYPES = {
    'google': [('google_sheet', 'google_sheet'), ('excel', 'excel'), ('csv', 'csv'), ('geojson', 'geojson')]
}

INDIVIDUAL_STATUSES = [('active', 'active'), ('broken', 'broken'), ('inactive', 'inactive')]

OUTPUT_STATUSES = [('connected', 'connected'), ('disconnected', 'disconnected'), ('pending', 'pending')]
OUTPUT_TYPES = [('output_agol', 'output_agol'), ('output_database', 'output_database'), ('output_kml', 'output_kml')]

REGISTRATION_METHODS = [('email', 'email'), ('google', 'google')]

RT_ACCOUNT_SOURCES = [('collar', 'collar'), ('radio', 'radio')]

SEXES = [('male', 'male'), ('female', 'female')]



# COLLAR_STATUSES = [('active', 'active'), ('broken', 'broken'), ('dead', 'dead'), ('unknown', 'unknown')]

# CHANGE_ACTIONS = [('create', 'create'), ('read', 'read'), ('update', 'update'), ('delete', 'delete')]
# CHANGE_TARGETS = [('collar_account', 'collar_account'), ('collar_individual', 'collar_individual')]