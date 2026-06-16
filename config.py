import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PORT = int(os.environ.get('PORT', 8330))
HOST = '0.0.0.0'
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

DATA_DIR = os.path.join(BASE_DIR, 'data')
TERM_BASE_FILE = os.path.join(DATA_DIR, 'term_base.json')
TRANSLATION_MEMORY_FILE = os.path.join(DATA_DIR, 'translation_memory.json')
ASYNC_TASKS_DIR = os.path.join(DATA_DIR, 'async_tasks')
MODEL_CACHE_DIR = os.path.join(DATA_DIR, 'model_cache')
FASTTEXT_MODEL_PATH = os.path.join(DATA_DIR, 'lid.176.bin')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASYNC_TASKS_DIR, exist_ok=True)
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

DEFAULT_MODEL_TYPE = 'opus-mt'
MULTILINGUAL_MODEL = 'Helsinki-NLP/opus-mt-mul-en'
PRELOAD_LANG_PAIRS = [
    ('zh', 'en'),
    ('en', 'zh'),
    ('en', 'es'),
    ('es', 'en'),
    ('en', 'ja'),
    ('ja', 'en'),
    ('en', 'fr'),
    ('fr', 'en'),
    ('en', 'de'),
    ('de', 'en'),
]

FUZZY_MATCH_THRESHOLD = 2
PARTIAL_MATCH_THRESHOLD = 0.85
PREFERRED_TTL_DAYS = 90

MAX_SYNC_TOKENS = 1024
ASYNC_TASK_TIMEOUT_SECONDS = 3600

SUPPORTED_LANGUAGES = {
    'zh': 'Chinese',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ru': 'Russian',
    'pt': 'Portuguese',
    'it': 'Italian',
    'nl': 'Dutch',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'id': 'Indonesian',
    'ms': 'Malay',
    'tr': 'Turkish',
    'pl': 'Polish',
    'sv': 'Swedish',
    'da': 'Danish',
    'fi': 'Finnish',
    'no': 'Norwegian',
    'cs': 'Czech',
    'el': 'Greek',
    'he': 'Hebrew',
}
