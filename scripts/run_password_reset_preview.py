"""Launch a local-only manual password-reset preview with disposable E2E data."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'http://127.0.0.1:8000'
MANUAL_EMAIL = 'e2e.password-reset-manual@example.test'
MANUAL_PASSWORD = 'E2E-Only-Password-2026!'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-reset-link', action='store_true', help='Verify the local reset link, then clean up.')
    options = parser.parse_args()
    temporary_directory = Path(tempfile.mkdtemp(prefix='eunoia-e2e-preview-'))
    environment = os.environ.copy()
    environment.update(
        {
            'EUNOIA_E2E': '1',
            'E2E_TEMP_DIR': str(temporary_directory),
            'E2E_DATABASE_PATH': str(temporary_directory / 'eunoia-e2e.sqlite3'),
            'DJANGO_SETTINGS_MODULE': 'config.settings_e2e',
            'DJANGO_DEBUG': 'True',
            # E2E settings reject a DATABASE_URL and never load .env.
            'DATABASE_URL': '',
        }
    )

    try:
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], cwd=ROOT, env=environment, check=True)
        subprocess.run([sys.executable, 'manage.py', 'seed_e2e_eunoia'], cwd=ROOT, env=environment, check=True)
        if options.verify_reset_link:
            os.environ.update(environment)
            sys.path.insert(0, str(ROOT))
            import django
            from django.core import mail
            from django.test import Client

            django.setup()
            client = Client()
            empty_outbox = client.get('/__e2e__/outbox/', HTTP_HOST='127.0.0.1:8000')
            if empty_outbox.status_code != 200 or empty_outbox.json() != {'emails': []}:
                raise RuntimeError('Empty local outbox did not return HTTP 200 with no messages.')
            response = client.post(
                '/password-reset/',
                {'email': MANUAL_EMAIL},
                HTTP_HOST='127.0.0.1:8000',
                REMOTE_ADDR='127.0.0.1',
            )
            if response.status_code != 302 or not mail.outbox:
                raise RuntimeError('Could not generate the local password-reset email.')
            match = re.search(r'http://127\.0\.0\.1:8000/password-reset/\S+', mail.outbox[-1].body)
            if match is None:
                raise RuntimeError('Local password-reset email did not contain the expected loopback link.')
            print('Verified empty local outbox: HTTP 200')
            print(f'Verified local reset link: {match.group(0)}')
            return
        print('\nPassword reset preview ready (local-only)')
        print(f'URL: {BASE_URL}/login/')
        print(f'Email: {MANUAL_EMAIL}')
        print(f'Current password: {MANUAL_PASSWORD}')
        print(f'Outbox: {BASE_URL}/__e2e__/outbox/')
        print('After requesting a reset, open Outbox and copy the local link from the latest email body.')
        print('Press Ctrl+C to stop the server and delete the temporary SQLite database.\n')
        subprocess.run([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'], cwd=ROOT, env=environment, check=True)
    except KeyboardInterrupt:
        pass
    finally:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        print('Preview stopped; temporary SQLite database deleted.')


if __name__ == '__main__':
    main()
