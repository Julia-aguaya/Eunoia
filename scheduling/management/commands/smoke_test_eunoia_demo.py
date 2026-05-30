from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from scheduling.demo import run_demo_smoke_flow


class Command(BaseCommand):
    help = 'Run a local end-to-end smoke test against the seeded demo accounts and pages.'

    def handle(self, *args, **options):
        client = Client()
        try:
            allowed_hosts = sorted(set([*settings.ALLOWED_HOSTS, 'testserver', 'localhost', '127.0.0.1']))
            with override_settings(ALLOWED_HOSTS=allowed_hosts):
                run_demo_smoke_flow(client=client, reverse_func=reverse)
        except Exception as exc:
            raise CommandError(f'Demo smoke test failed: {exc}') from exc

        self.stdout.write(self.style.SUCCESS('Demo smoke test: OK'))
        self.stdout.write('- student login, dashboard, agenda, bookings, reserve, cancel, and recovery flow passed')
        self.stdout.write('- staff login, student list, class agenda, and student detail flow passed')
