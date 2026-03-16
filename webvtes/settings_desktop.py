import os
from copy import deepcopy
from pathlib import Path

from .settings import *  # noqa: F401,F403


PORTABLE_DIR = Path(os.environ.get('WEBVTES_PORTABLE_DIR', BASE_DIR))
PORTABLE_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = deepcopy(DATABASES)
DATABASES['default'] = deepcopy(DATABASES['default'])
DATABASES['default']['NAME'] = PORTABLE_DIR / 'db.sqlite3'

MEDIA_ROOT = PORTABLE_DIR / 'media'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
