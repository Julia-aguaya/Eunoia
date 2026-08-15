#!/usr/bin/env bash
set -euo pipefail
umask 077

project_dir="$HOME/eunoia"
env_file="$project_dir/.env"
state_dir="$HOME/eunoia-resend-maintenance"
# This is the existing service name used by deploy-eunoia.sh.
service_name='eunoia'

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

[[ -n "${RESEND_SMTP_API_KEY:-}" ]] || fail 'RESEND_SMTP_API_KEY is required.'
[[ "$RESEND_SMTP_API_KEY" != *$'\n'* && "$RESEND_SMTP_API_KEY" != *$'\r'* ]] || fail 'RESEND_SMTP_API_KEY must be a single line.'
[[ -f "$env_file" ]] || fail 'Production .env is missing.'
[[ -x "$project_dir/.venv/bin/python" ]] || fail 'Production virtual environment is missing.'
"$project_dir/.venv/bin/python" -c 'from anymail.backends.resend import EmailBackend'

[[ ! -L "$state_dir" ]] || fail 'Resend maintenance directory must not be a symlink.'
mkdir -p "$state_dir"
chmod 700 "$state_dir"
[[ -d "$state_dir" && ! -L "$state_dir" && "$(stat -c '%a' "$state_dir")" == '700' ]] || fail 'Resend maintenance directory permissions are invalid.'

exec 9>"$state_dir/configure-resend-api.lock"
flock -n 9 || fail 'Another Resend API configuration is already running.'

backup_file="$(mktemp "$state_dir/.env.resend-backup.$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")"
temporary_file="$(mktemp "$state_dir/.env.resend-tmp.XXXXXX")"
chmod 600 "$temporary_file"
cp --preserve=mode,timestamps "$env_file" "$backup_file"
chmod 600 "$backup_file"

restore_backup_on_failure() {
  local status=$?
  if [[ "$status" -ne 0 ]]; then
    cp --preserve=mode,timestamps "$backup_file" "$env_file"
    chmod 600 "$env_file"
    sudo -n systemctl restart "$service_name" || true
  fi
  rm -f "$temporary_file"
  return "$status"
}

trap restore_backup_on_failure EXIT

EUNOIA_ENV_FILE="$env_file" \
EUNOIA_ENV_TEMP_FILE="$temporary_file" \
RESEND_SMTP_API_KEY="$RESEND_SMTP_API_KEY" \
"$project_dir/.venv/bin/python" - <<'PY'
import os
import re

env_file = os.environ['EUNOIA_ENV_FILE']
temporary_file = os.environ['EUNOIA_ENV_TEMP_FILE']
values = {
    'EMAIL_BACKEND': 'anymail.backends.resend.EmailBackend',
    'ANYMAIL_RESEND_API_KEY': os.environ['RESEND_SMTP_API_KEY'],
    'DEFAULT_FROM_EMAIL': '"Eunoia <no-reply@mail.pilateseunoia.com>"',
    'PASSWORD_RESET_TIMEOUT': '3600',
    'EUNOIA_PUBLIC_ORIGIN': 'https://pilateseunoia.com',
}
removed_keys = {
    'EMAIL_HOST',
    'EMAIL_PORT',
    'EMAIL_USE_SSL',
    'EMAIL_USE_TLS',
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
}

with open(env_file, 'r', encoding='utf-8', newline='') as source:
    lines = source.readlines()

seen = set()
with open(temporary_file, 'w', encoding='utf-8', newline='') as target:
    for line in lines:
        match = re.match(r'^([A-Z0-9_]+)=', line)
        key = match.group(1) if match else None
        if key in removed_keys:
            continue
        if key not in values:
            target.write(line)
            continue
        if key not in seen:
            target.write(f'{key}={values[key]}\n')
            seen.add(key)
    for key, value in values.items():
        if key not in seen:
            target.write(f'{key}={value}\n')
    target.flush()
    os.fsync(target.fileno())

PY

mv -- "$temporary_file" "$env_file"
chmod 600 "$env_file"

cd "$project_dir"
.venv/bin/python - <<'PY'
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from anymail.backends.resend import EmailBackend
from django.conf import settings

expected = {
    'EMAIL_BACKEND': 'anymail.backends.resend.EmailBackend',
    'DEFAULT_FROM_EMAIL': 'Eunoia <no-reply@mail.pilateseunoia.com>',
    'PASSWORD_RESET_TIMEOUT': 3600,
    'EUNOIA_PUBLIC_ORIGIN': 'https://pilateseunoia.com',
}

if not settings.ANYMAIL.get('RESEND_API_KEY'):
    raise SystemExit('Resend API configuration validation failed: key is empty.')

for name, value in expected.items():
    if getattr(settings, name) != value:
        raise SystemExit(f'Resend API configuration validation failed: {name}.')

EmailBackend()

print(f'backend={settings.EMAIL_BACKEND}')
print(f'public_origin={settings.EUNOIA_PUBLIC_ORIGIN}')
print(f'from_email={settings.DEFAULT_FROM_EMAIL}')
print('resend_api_https=deferred_controlled_smoke_test')
PY
.venv/bin/python manage.py check

sudo -n systemctl restart "$service_name"
trap - EXIT
rm -f "$temporary_file"
printf '%s\n' 'Resend API configuration applied and validated.'
