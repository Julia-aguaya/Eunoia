#!/usr/bin/env bash
set -euo pipefail
umask 077

project_dir="$HOME/eunoia"
env_file="$project_dir/.env"
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

exec 9>"$project_dir/.configure-resend-smtp.lock"
flock -n 9 || fail 'Another Resend SMTP configuration is already running.'

backup_file="$env_file.resend-backup.$(date -u +%Y%m%dT%H%M%SZ)"
temporary_file="$(mktemp "$project_dir/.env.resend-tmp.XXXXXX")"
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
    'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
    'EMAIL_HOST': 'smtp.resend.com',
    'EMAIL_PORT': '465',
    'EMAIL_USE_SSL': 'True',
    'EMAIL_USE_TLS': 'False',
    'EMAIL_HOST_USER': 'resend',
    'EMAIL_HOST_PASSWORD': os.environ['RESEND_SMTP_API_KEY'],
    'DEFAULT_FROM_EMAIL': '"Eunoia <no-reply@mail.pilateseunoia.com>"',
    'PASSWORD_RESET_TIMEOUT': '3600',
    'EUNOIA_PUBLIC_ORIGIN': 'https://pilateseunoia.com',
}

with open(env_file, 'r', encoding='utf-8', newline='') as source:
    lines = source.readlines()

seen = set()
with open(temporary_file, 'w', encoding='utf-8', newline='') as target:
    for line in lines:
        match = re.match(r'^([A-Z0-9_]+)=', line)
        key = match.group(1) if match else None
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

os.replace(temporary_file, env_file)
os.chmod(env_file, 0o600)
PY

cd "$project_dir"
.venv/bin/python - <<'PY'
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from django.conf import settings

expected = {
    'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
    'EMAIL_HOST': 'smtp.resend.com',
    'EMAIL_PORT': 465,
    'EMAIL_USE_SSL': True,
    'EMAIL_USE_TLS': False,
    'EMAIL_HOST_USER': 'resend',
    'DEFAULT_FROM_EMAIL': 'Eunoia <no-reply@mail.pilateseunoia.com>',
    'PASSWORD_RESET_TIMEOUT': 3600,
    'EUNOIA_PUBLIC_ORIGIN': 'https://pilateseunoia.com',
}

if not settings.EMAIL_HOST_PASSWORD:
    raise SystemExit('SMTP configuration validation failed: password is empty.')

for name, value in expected.items():
    if getattr(settings, name) != value:
        raise SystemExit(f'SMTP configuration validation failed: {name}.')

print(f'backend={settings.EMAIL_BACKEND}')
print(f'host={settings.EMAIL_HOST}')
print(f'port={settings.EMAIL_PORT}')
print(f'ssl={settings.EMAIL_USE_SSL}')
print(f'public_origin={settings.EUNOIA_PUBLIC_ORIGIN}')
print(f'from_email={settings.DEFAULT_FROM_EMAIL}')
PY
.venv/bin/python manage.py check

sudo -n systemctl restart "$service_name"
trap - EXIT
rm -f "$temporary_file"
printf '%s\n' 'Resend SMTP configuration applied and validated.'
