import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ._shared import *


class E2ESettingsGuardsTests(TestCase):
    def test_healthcheck_is_hidden_in_normal_configuration(self):
        response = self.client.get('/healthz/')

        self.assertEqual(response.status_code, 404)

    def run_settings_import(self, environment):
        result = subprocess.run(
            [sys.executable, '-c', 'import config.settings_e2e'],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            capture_output=True,
            text=True,
        )
        return result.stderr

    def test_settings_reject_without_explicit_e2e_opt_in(self):
        environment = os.environ.copy()
        environment.pop('EUNOIA_E2E', None)

        self.assertIn('E2E settings require EUNOIA_E2E=1.', self.run_settings_import(environment))

    def test_settings_reject_database_url_even_with_opt_in(self):
        environment = os.environ.copy()
        environment.update({'EUNOIA_E2E': '1', 'DATABASE_URL': 'sqlite:///unsafe.sqlite3'})

        self.assertIn('E2E settings reject DATABASE_URL.', self.run_settings_import(environment))

    def test_settings_require_runner_owned_database_directory(self):
        with tempfile.TemporaryDirectory(prefix='not-e2e-') as temporary_directory:
            environment = os.environ.copy()
            environment.update({
                'EUNOIA_E2E': '1',
                'DATABASE_URL': '',
                'DJANGO_DEBUG': 'True',
                'E2E_TEMP_DIR': temporary_directory,
                'E2E_DATABASE_PATH': str(Path(temporary_directory) / 'eunoia-e2e.sqlite3'),
            })

            self.assertIn('runner-created eunoia-e2e temporary directory', self.run_settings_import(environment))


class E2ESeedGuardsTests(TestCase):
    def test_seed_rejects_the_regular_test_database(self):
        with self.assertRaisesMessage(CommandError, 'E2E seed is disabled'):
            call_command('seed_e2e_eunoia')

        self.assertFalse(User.objects.filter(email='e2e.staff@example.test').exists())
