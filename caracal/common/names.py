
import random

from account.models import Organization


def generate_unique_short_name():

    while True:

        short_name = f'{random.choice(adjectives)}-{random.choice(nouns)}'

        try:
            Organization.objects.get(short_name=short_name)
        except Organization.DoesNotExist:
            return short_name


adjectives = [
    'alive', 'ambitious', 'ancient', 'autumn', 'billowing', 'better', 'bitter', 'black', 'blue', 'bold',
    'brave', 'broad', 'calm', 'cold', 'colossal', 'cool', 'crashing', 'crimson',
    'dark', 'delicate', 'divine', 'dry', 'echoing', 'falling', 'fancy',
    'flat', 'floral', 'fragrant', 'frosty', 'future', 'gentle', 'gifted', 'green', 'hidden', 'holy',
    'icy', 'jolly', 'kind', 'late', 'little', 'lively', 'lucky',
    'mammoth', 'melodic', 'misty', 'mute',
    'orange', 'patient', 'polished', 'proud', 'purple', 'quiet', 'rapid',
    'raspy', 'red', 'restless', 'rich', 'rough', 'round', 'royal', 'rhythmic', 'shiny',
    'shy', 'silent', 'small', 'snowy', 'soft', 'solitary', 'sparkling', 'spring',
    'square', 'steep', 'still', 'summer', 'super', 'sweet', 'tender', 'thundering',
    'twilight', 'wandering', 'weathered', 'white', 'wild', 'winter', 'witty',
    'yellow', 'young'
]


nouns = [
    'base', 'bird',
    'breeze', 'brook', 'butterfly', 'cake', 'cell', 'cherry',
    'cloud', 'darkness', 'dawn', 'dew', 'disk', 'dream', 'dust',
    'feather', 'field', 'fire', 'firefly', 'flower', 'fog', 'forest', 'frog',
    'frost', 'glade', 'glitter', 'grass', 'hall', 'haze', 'heart',
    'hill', 'king', 'lab', 'lake', 'leaf', 'limit', 'math', 'meadow',
    'mode', 'moon', 'morning', 'mountain', 'mouse', 'mud', 'night', 'paper',
    'pine', 'poetry', 'pond', 'queen', 'rain', 'recipe', 'resonance', 'rice',
    'river', 'salad', 'scene', 'sea', 'shadow', 'shape', 'silence', 'sky',
    'smoke', 'snow', 'snowflake', 'sound', 'star', 'sun', 'sun', 'sunset',
    'surf', 'term', 'thunder', 'tooth', 'tree', 'truth', 'union',
    'violet', 'voice', 'water', 'waterfall', 'wave', 'wildflower', 'wind'
]