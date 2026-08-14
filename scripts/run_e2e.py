"""Run Playwright against a disposable, deterministic Django E2E environment."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'http://127.0.0.1:8000'


def wait_for_health(server):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError('E2E Django server exited before becoming healthy.')
        try:
            with urlopen(f'{BASE_URL}/healthz/', timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError('E2E Django server did not become healthy within 20 seconds.')


def main():
    with tempfile.TemporaryDirectory(prefix='eunoia-e2e-') as temporary_directory:
        temp_dir = Path(temporary_directory)
        environment = os.environ.copy()
        environment.update({
            'EUNOIA_E2E': '1',
            'E2E_TEMP_DIR': str(temp_dir),
            'E2E_DATABASE_PATH': str(temp_dir / 'eunoia-e2e.sqlite3'),
            'DJANGO_SETTINGS_MODULE': 'config.settings_e2e',
            'DJANGO_DEBUG': 'True',
            # Prevent config.settings from accepting a shell or .env database URL.
            'DATABASE_URL': '',
        })
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], cwd=ROOT, env=environment, check=True)
        subprocess.run([sys.executable, 'manage.py', 'seed_e2e_eunoia'], cwd=ROOT, env=environment, check=True)

        log_file = (temp_dir / 'e2e-server.log').open('w', encoding='utf-8')
        server = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
            cwd=ROOT,
            env=environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        try:
            wait_for_health(server)
            npx = shutil.which('npx') or ('npx.cmd' if os.name == 'nt' else 'npx')
            subprocess.run([npx, 'playwright', 'test'], cwd=ROOT, env={**environment, 'E2E_BASE_URL': BASE_URL}, check=True)
        finally:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(server.pid), '/T', '/F'], capture_output=True, check=False)
            else:
                server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            log_file.close()


if __name__ == '__main__':
    main()
