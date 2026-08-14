import re
from urllib.parse import urlsplit

from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from scheduling.models import MonthlyAccessStatus, MonthlyAccessStatusType, PasswordResetRateLimit, Section, User


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.password = 'AnteriorSegura2026!'
        self.user = self.create_user('activa@example.com')

    def create_user(self, email, *, active=True):
        return User.objects.create_user(
            email=email,
            password=self.password,
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
            is_active=active,
            must_change_password=False,
        )

    def request_reset(self, email, **extra):
        remote_addr = extra.pop('REMOTE_ADDR', '198.51.100.18')
        return self.client.post(reverse('password-reset'), {'email': email}, REMOTE_ADDR=remote_addr, **extra)

    def extract_reset_path(self, email):
        match = re.search(r'https://pilateseunoia\.com(?P<path>/password-reset/[^\s]+)', email.body)
        self.assertIsNotNone(match)
        return urlsplit(match.group('path')).path

    def test_existing_and_unknown_addresses_receive_the_same_neutral_response(self):
        existing = self.request_reset(self.user.email)
        existing_body = existing.content.decode()
        unknown = self.request_reset('desconocida@example.com')

        self.assertRedirects(existing, reverse('password-reset-done'))
        self.assertRedirects(unknown, reverse('password-reset-done'))
        self.assertEqual(existing_body, unknown.content.decode())
        self.assertEqual(len(mail.outbox), 1)

    def test_email_uses_fixed_https_public_origin(self):
        self.request_reset(self.user.email)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('https://pilateseunoia.com/password-reset/', mail.outbox[0].body)
        self.assertNotIn('http://testserver', mail.outbox[0].body)

    @override_settings(
        EUNOIA_E2E=True,
        E2E_PASSWORD_RESET_EMAIL_DOMAIN='127.0.0.1:8000',
        E2E_PASSWORD_RESET_EMAIL_USE_HTTPS=False,
    )
    def test_e2e_preview_email_uses_local_loopback_origin(self):
        self.request_reset(self.user.email)

        self.assertIn('http://127.0.0.1:8000/password-reset/', mail.outbox[0].body)
        self.assertNotIn('https://pilateseunoia.com/password-reset/', mail.outbox[0].body)

    def test_e2e_outbox_route_is_unavailable_outside_e2e_mode(self):
        response = self.client.get('/__e2e__/outbox/')

        self.assertEqual(response.status_code, 404)

    def test_inactive_and_suspended_accounts_do_not_reveal_account_existence(self):
        inactive = self.create_user('inactiva@example.com', active=False)
        suspended = self.create_user('suspendida@example.com')
        MonthlyAccessStatus.objects.create(
            student=suspended,
            month=timezone.localdate().replace(day=1),
            status=MonthlyAccessStatusType.SUSPENDED,
            booking_enabled=False,
        )

        inactive_response = self.request_reset(inactive.email)
        suspended_response = self.request_reset(suspended.email)

        self.assertRedirects(inactive_response, reverse('password-reset-done'))
        self.assertRedirects(suspended_response, reverse('password-reset-done'))
        self.assertEqual(len(mail.outbox), 1)  # Active but operationally suspended accounts remain recoverable.

    def test_valid_token_changes_password_invalidates_sessions_and_cannot_be_reused(self):
        old_session = Client()
        old_session.force_login(self.user)
        old_session_key = old_session.session.session_key
        self.request_reset(self.user.email)
        reset_path = self.extract_reset_path(mail.outbox[0])

        initial = self.client.get(reset_path)
        confirmation_path = urlsplit(initial['Location']).path
        response = self.client.post(
            confirmation_path,
            {'new_password1': 'NuevaSegura2026!', 'new_password2': 'NuevaSegura2026!'},
        )

        self.assertRedirects(response, reverse('password-reset-complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaSegura2026!'))
        self.assertFalse(self.user.check_password(self.password))
        self.assertFalse(Session.objects.filter(session_key=old_session_key).exists())
        self.assertRedirects(old_session.get(reverse('dashboard')), f"{reverse('login')}?next={reverse('dashboard')}")
        reused = self.client.get(reset_path)
        self.assertContains(reused, 'El enlace ya no es válido')

    def test_altered_and_expired_tokens_are_rejected(self):
        self.request_reset(self.user.email)
        reset_path = self.extract_reset_path(mail.outbox[0])
        altered = f"{reset_path.rstrip('/')[:-1]}x/"
        self.assertContains(self.client.get(altered), 'El enlace ya no es válido')

        uidb64 = reset_path.split('/')[2]
        expired_token = default_token_generator._make_token_with_timestamp(self.user, 0, default_token_generator.secret)
        expired_path = reverse('password-reset-confirm', kwargs={'uidb64': uidb64, 'token': expired_token})
        self.assertContains(self.client.get(expired_path), 'El enlace ya no es válido')

    def test_email_and_ip_limits_return_the_same_neutral_response(self):
        for _ in range(3):
            self.request_reset('email-limit@example.com')
        fourth = self.request_reset('email-limit@example.com')
        self.assertRedirects(fourth, reverse('password-reset-done'))
        self.assertEqual(len(mail.outbox), 0)

        for number in range(5):
            self.request_reset(f'ip-limit-{number}@example.com', REMOTE_ADDR='203.0.113.50')
        sixth = self.request_reset('ip-limit-final@example.com', REMOTE_ADDR='203.0.113.50')
        self.assertRedirects(sixth, reverse('password-reset-done'))
        self.assertEqual(PasswordResetRateLimit.objects.filter(scope='ip').count(), 2)

    def test_csrf_is_required(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.get(reverse('password-reset'))

        response = csrf_client.post(reverse('password-reset'), {'email': self.user.email})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_logs_do_not_contain_email_or_token(self):
        with self.assertLogs('scheduling.password_reset', level='INFO') as logs:
            self.request_reset(self.user.email)

        rendered_logs = '\n'.join(logs.output)
        self.assertNotIn(self.user.email, rendered_logs)
        self.assertNotIn(mail.outbox[0].body, rendered_logs)
