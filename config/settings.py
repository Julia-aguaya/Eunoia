import os
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


def load_env_file(env_path):
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    value = os.getenv(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


def csrf_origin_candidates(host):
    normalized_host = host.strip()
    if not normalized_host or normalized_host == '*':
        return []

    if normalized_host.startswith('.'):
        normalized_host = f'*{normalized_host}'

    schemes = ['https']
    if normalized_host in {'localhost', '127.0.0.1', '[::1]'}:
        schemes = ['http', 'https']

    return [f'{scheme}://{normalized_host}' for scheme in schemes]


def build_csrf_trusted_origins(allowed_hosts, configured_origins=None):
    trusted_origins = []
    seen = set()

    for origin in configured_origins or []:
        if origin not in seen:
            trusted_origins.append(origin)
            seen.add(origin)

    for host in allowed_hosts or []:
        for origin in csrf_origin_candidates(host):
            if origin not in seen:
                trusted_origins.append(origin)
                seen.add(origin)

    return trusted_origins


def _normalized_host_pattern(host):
    normalized_host = host.strip().split(':', 1)[0]
    if not normalized_host or normalized_host == '*':
        return ''

    if normalized_host.startswith('*.'):
        normalized_host = normalized_host[2:]
    elif normalized_host.startswith('.'):
        normalized_host = normalized_host[1:]

    return normalized_host.strip().lower()


def _is_ip_address(value):
    try:
        ip_address(value.strip('[]'))
    except ValueError:
        return False
    return True


def normalize_cookie_domain(domain):
    normalized_domain = domain.strip().lower()
    if not normalized_domain:
        return None
    if normalized_domain.startswith('*.'):
        normalized_domain = normalized_domain[1:]
    if not normalized_domain.startswith('.'):
        normalized_domain = f'.{normalized_domain}'
    return normalized_domain


def build_cookie_domain(allowed_hosts, configured_domain=''):
    if configured_domain:
        return normalize_cookie_domain(configured_domain)

    domain_hosts = []
    wildcard_domains = []
    seen_hosts = set()
    for host in allowed_hosts or []:
        normalized_host = _normalized_host_pattern(host)
        if (
            not normalized_host
            or normalized_host == 'localhost'
            or '.' not in normalized_host
            or _is_ip_address(normalized_host)
        ):
            continue
        if normalized_host not in seen_hosts:
            domain_hosts.append(normalized_host)
            seen_hosts.add(normalized_host)
        if host.strip().startswith(('*.', '.')):
            wildcard_domains.append(normalize_cookie_domain(normalized_host))

    if wildcard_domains:
        return sorted(set(wildcard_domains), key=len)[0]

    if not domain_hosts:
        return None

    candidate = min(domain_hosts, key=len)
    if all(host == candidate or host.endswith(f'.{candidate}') for host in domain_hosts):
        return normalize_cookie_domain(candidate)

    return None


def env_int(name, default=0):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value.strip())


def postgres_extra_config(query_pairs=None):
    query_pairs = query_pairs or {}
    options = {}

    ssl_mode = query_pairs.get('sslmode') or os.getenv('DJANGO_DB_SSL_MODE', '').strip()
    if ssl_mode:
        options['sslmode'] = ssl_mode

    connect_timeout = query_pairs.get('connect_timeout') or os.getenv('DJANGO_DB_CONNECT_TIMEOUT', '').strip()
    if connect_timeout:
        options['connect_timeout'] = int(connect_timeout)

    config = {
        'CONN_MAX_AGE': int(query_pairs.get('conn_max_age') or env_int('DJANGO_DB_CONN_MAX_AGE', 60)),
        'CONN_HEALTH_CHECKS': env_bool('DJANGO_DB_CONN_HEALTH_CHECKS', default=True),
    }
    if options:
        config['OPTIONS'] = options
    return config


def mysql_extra_config(query_pairs=None):
    query_pairs = query_pairs or {}
    options = {
        'charset': query_pairs.get('charset') or os.getenv('DJANGO_DB_CHARSET', 'utf8mb4').strip() or 'utf8mb4',
    }

    init_command = query_pairs.get('init_command') or os.getenv('DJANGO_DB_INIT_COMMAND', '').strip()
    sql_mode = query_pairs.get('sql_mode') or os.getenv('DJANGO_DB_SQL_MODE', '').strip()
    if sql_mode:
        options['init_command'] = f"SET sql_mode='{sql_mode}'"
    elif init_command:
        options['init_command'] = init_command

    connect_timeout = query_pairs.get('connect_timeout') or os.getenv('DJANGO_DB_CONNECT_TIMEOUT', '').strip()
    if connect_timeout:
        options['connect_timeout'] = int(connect_timeout)

    ssl = {}
    ssl_ca = query_pairs.get('ssl_ca') or os.getenv('DJANGO_DB_SSL_CA', '').strip()
    ssl_cert = query_pairs.get('ssl_cert') or os.getenv('DJANGO_DB_SSL_CERT', '').strip()
    ssl_key = query_pairs.get('ssl_key') or os.getenv('DJANGO_DB_SSL_KEY', '').strip()
    if ssl_ca:
        ssl['ca'] = ssl_ca
    if ssl_cert:
        ssl['cert'] = ssl_cert
    if ssl_key:
        ssl['key'] = ssl_key
    if ssl:
        options['ssl'] = ssl

    return {
        'CONN_MAX_AGE': int(query_pairs.get('conn_max_age') or env_int('DJANGO_DB_CONN_MAX_AGE', 60)),
        'CONN_HEALTH_CHECKS': env_bool('DJANGO_DB_CONN_HEALTH_CHECKS', default=True),
        'OPTIONS': options,
    }


def parse_database_url(database_url):
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {'postgres', 'postgresql'}:
        config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': unquote(parsed.path.lstrip('/')),
            'USER': unquote(parsed.username or ''),
            'PASSWORD': unquote(parsed.password or ''),
            'HOST': parsed.hostname or '',
            'PORT': str(parsed.port or ''),
        }
        config.update(postgres_extra_config(dict(parse_qsl(parsed.query, keep_blank_values=False))))
        return config

    if scheme in {'mysql', 'mysql2', 'mysql+mysqlclient', 'mariadb'}:
        config = {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': unquote(parsed.path.lstrip('/')),
            'USER': unquote(parsed.username or ''),
            'PASSWORD': unquote(parsed.password or ''),
            'HOST': parsed.hostname or '',
            'PORT': str(parsed.port or ''),
        }
        config.update(mysql_extra_config(dict(parse_qsl(parsed.query, keep_blank_values=False))))
        return config

    if scheme == 'sqlite':
        sqlite_path = unquote(parsed.path or '')
        if parsed.netloc and parsed.netloc not in {'', 'localhost'}:
            sqlite_path = f'//{parsed.netloc}{sqlite_path}'
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': Path(sqlite_path or str(BASE_DIR / 'db.sqlite3')),
        }

    raise ValueError(f'Unsupported database scheme: {parsed.scheme}')


def database_config():
    database_url = os.getenv('DATABASE_URL', '').strip()
    if database_url:
        return parse_database_url(database_url)

    engine = os.getenv('DJANGO_DB_ENGINE', '').strip()
    if engine == 'django.db.backends.sqlite3':
        return {
            'ENGINE': engine,
            'NAME': Path(os.getenv('DJANGO_DATABASE_PATH', str(BASE_DIR / 'db.sqlite3'))),
        }

    if engine:
        config = {
            'ENGINE': engine,
            'NAME': os.getenv('DJANGO_DB_NAME', ''),
            'USER': os.getenv('DJANGO_DB_USER', ''),
            'PASSWORD': os.getenv('DJANGO_DB_PASSWORD', ''),
            'HOST': os.getenv('DJANGO_DB_HOST', ''),
            'PORT': os.getenv('DJANGO_DB_PORT', ''),
        }
        if engine == 'django.db.backends.postgresql':
            config.update(postgres_extra_config())
        if engine == 'django.db.backends.mysql':
            config.update(mysql_extra_config())
        return config

    if env_bool('DJANGO_USE_SQLITE', default=env_bool('DJANGO_DEBUG', default=True)):
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': Path(os.getenv('DJANGO_DATABASE_PATH', str(BASE_DIR / 'db.sqlite3'))),
        }

    raise ImproperlyConfigured(
        'Database configuration missing. Set DATABASE_URL for MySQL in production, '
        'or set DJANGO_USE_SQLITE=True for local/demo environments.'
    )


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_env_file(BASE_DIR / '.env')


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-dev-only-secret-key')
DEBUG = env_bool('DJANGO_DEBUG', default=True)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
configured_csrf_trusted_origins = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])
configured_cookie_domain = os.getenv('DJANGO_COOKIE_DOMAIN', '').strip()

render_external_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if render_external_hostname and render_external_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_external_hostname)
CSRF_TRUSTED_ORIGINS = build_csrf_trusted_origins(ALLOWED_HOSTS, configured_csrf_trusted_origins)
COOKIE_DOMAIN = build_cookie_domain(ALLOWED_HOSTS, configured_cookie_domain)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'scheduling',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'scheduling.middleware.MustChangePasswordMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': database_config()
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-ar'

TIME_ZONE = 'America/Argentina/Buenos_Aires'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_ROOT.mkdir(exist_ok=True)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = env_bool('DJANGO_USE_X_FORWARDED_HOST', default=bool(render_external_hostname))
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_DOMAIN = COOKIE_DOMAIN
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_DOMAIN = COOKIE_DOMAIN
SECURE_CONTENT_TYPE_NOSNIFF = not DEBUG
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', default=False)
SECURE_REFERRER_POLICY = os.getenv('DJANGO_SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin')

AUTH_USER_MODEL = 'scheduling.User'
EUNOIA_DEFAULT_TEMPORARY_PASSWORD = os.getenv('EUNOIA_DEFAULT_TEMPORARY_PASSWORD', 'EunoiaTemp2026!')
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
