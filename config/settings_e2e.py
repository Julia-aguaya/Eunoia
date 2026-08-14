"""Hard-isolated settings for local Playwright E2E runs only."""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.utils import timezone

if os.getenv('EUNOIA_E2E') != '1':
    raise RuntimeError('E2E settings require EUNOIA_E2E=1.')
if os.getenv('DATABASE_URL', '').strip():
    raise RuntimeError('E2E settings reject DATABASE_URL.')

from .settings import *  # noqa: F403,E402

if not DEBUG:  # noqa: F405
    raise RuntimeError('E2E settings require DEBUG=True.')
if os.getenv('DATABASE_URL', '').strip():
    raise RuntimeError('E2E settings reject DATABASE_URL.')

try:
    database_path = Path(os.environ['E2E_DATABASE_PATH']).resolve(strict=False)
    temp_dir = Path(os.environ['E2E_TEMP_DIR']).resolve(strict=True)
except KeyError as exc:
    raise RuntimeError('E2E settings require E2E_DATABASE_PATH and E2E_TEMP_DIR.') from exc

if (
    database_path.parent != temp_dir
    or not temp_dir.is_dir()
    or not temp_dir.name.startswith('eunoia-e2e-')
    or database_path.name != 'eunoia-e2e.sqlite3'
    or database_path.suffix != '.sqlite3'
):
    raise RuntimeError('E2E database must be eunoia-e2e.sqlite3 inside the runner-created eunoia-e2e temporary directory.')

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': database_path}}
SECRET_KEY = 'e2e-only-not-a-production-secret'
DEBUG = True
EUNOIA_E2E = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1', 'http://localhost']
TIME_ZONE = 'America/Argentina/Cordoba'
E2E_FIXED_DATE = '2026-08-10'
E2E_FIXED_NOW = timezone.make_aware(datetime(2026, 8, 10, 8, 0), ZoneInfo(TIME_ZONE))
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
E2E_PASSWORD_RESET_EMAIL_DOMAIN = '127.0.0.1:8000'
E2E_PASSWORD_RESET_EMAIL_USE_HTTPS = False


def _e2e_now():
    return E2E_FIXED_NOW


# All app code obtains the clock through django.utils.timezone. Freezing it here
# keeps the seed, server process, and browser assertions on one stable workweek.
timezone.now = _e2e_now
