import re

from django.test import Client, SimpleTestCase

from config.settings import build_csrf_trusted_origins, csrf_origin_candidates

from ._shared import *


class CsrfSettingsTests(SimpleTestCase):
    def test_build_csrf_trusted_origins_adds_https_origins_for_allowed_hosts(self):
        trusted_origins = build_csrf_trusted_origins(
            ['pilateseunoia.com', '.pilateseunoia.com', 'localhost', '*'],
            configured_origins=['https://already-configured.example.com'],
        )

        self.assertEqual(
            trusted_origins,
            [
                'https://already-configured.example.com',
                'https://pilateseunoia.com',
                'https://*.pilateseunoia.com',
                'http://localhost',
                'https://localhost',
            ],
        )

    def test_csrf_origin_candidates_skips_empty_and_wildcard_hosts(self):
        self.assertEqual(csrf_origin_candidates(''), [])
        self.assertEqual(csrf_origin_candidates('*'), [])

class UserOnboardingTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')

    def test_login_sets_referrer_policy_header_for_https_form_posts(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.headers['Referrer-Policy'], 'strict-origin-when-cross-origin')

    def test_set_temporary_password_hashes_value_and_flags_first_login_reset(self):
        user = User.objects.create_user(
            email='student-onboarding@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            must_change_password=False,
        )

        user.set_temporary_password('NuevaTemp2026!')
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.check_password('NuevaTemp2026!'))
        self.assertTrue(user.must_change_password)
        self.assertIsNotNone(user.temporary_password_set_at)

    def test_setting_permanent_password_clears_temporary_password_tracking(self):
        user = User.objects.create_user(
            email='student-permanent@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
        )

        user.set_initial_password('Definitiva2026!', require_password_change=False)
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.check_password('Definitiva2026!'))
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='OnboardingTemp2026!')
    def test_reset_temporary_password_use_case_uses_default_password_without_duplicating_model_rules(self):
        user = User.objects.create_user(
            email='student-reset@example.com',
            password='secret123',
            first_name='Hedy',
            last_name='Lamarr',
            must_change_password=False,
        )

        result = reset_temporary_password(users=User.objects.filter(pk=user.pk))

        user.refresh_from_db()
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(get_default_temporary_password(), 'OnboardingTemp2026!')
        self.assertTrue(user.check_password('OnboardingTemp2026!'))
        self.assertTrue(user.must_change_password)
        self.assertIsNotNone(user.temporary_password_set_at)

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='AltaManualTemp2026!')
    def test_create_student_onboarding_uses_default_password_and_model_flags(self):
        user = create_student_onboarding(
            email='alta-manual@example.com',
            first_name='Katherine',
            last_name='Johnson',
            primary_section=self.section,
            notes='Alta manual',
            must_change_password=False,
        )

        self.assertTrue(user.check_password('AltaManualTemp2026!'))
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)
        self.assertEqual(user.primary_section, self.section)

class UserAdminActionTests(TestCase):
    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='AdminActionTemp2026!')
    def test_reset_temporary_password_action_uses_onboarding_use_case(self):
        section = Section.objects.get(code='cadillac')
        acting_user = User.objects.create_user(
            email='staff-action@example.com',
            password='AdminSecret2026!',
            first_name='Staff',
            last_name='Action',
            role='admin',
            is_staff=True,
            primary_section=section,
        )
        target_user = User.objects.create_user(
            email='student-action@example.com',
            password='secret123',
            first_name='Student',
            last_name='Action',
            primary_section=section,
            must_change_password=False,
        )
        request = HttpRequest()
        request.user = acting_user
        admin_site = AdminSite()
        model_admin = UserAdmin(User, admin_site)
        messages = []
        model_admin.message_user = lambda _request, message: messages.append(message)

        reset_temporary_passwords(model_admin, request, User.objects.filter(pk=target_user.pk))

        target_user.refresh_from_db()
        self.assertTrue(target_user.check_password('AdminActionTemp2026!'))
        self.assertTrue(target_user.must_change_password)
        self.assertEqual(
            messages,
            ['Se resetearon 1 usuarias con la contrasena temporal configurada y cambio obligatorio en primer ingreso.'],
        )

class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.today = timezone.localdate()

    def assert_never_cache_headers(self, response):
        cache_control = response.headers['Cache-Control']
        for directive in ('max-age=0', 'no-cache', 'no-store', 'must-revalidate', 'private'):
            self.assertIn(directive, cache_control)

    def create_student(self, *, email, password, must_change_password):
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
            must_change_password=must_change_password,
        )
        if not must_change_password:
            user.temporary_password_set_at = None
            user.save(update_fields=['temporary_password_set_at', 'updated_at'])
        return user

    def create_future_session(self, *, days=3, start_hour=9):
        return ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=days),
            start_time=time(start_hour, 0),
            end_time=time(start_hour + 1, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )

    def test_login_succeeds_with_valid_credentials(self):
        user = self.create_student(
            email='login-ok@example.com',
            password='TempLogin2026!',
            must_change_password=False,
        )

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'TempLogin2026!'},
        )

        self.assertRedirects(response, reverse('dashboard'))
        follow_response = self.client.get(reverse('dashboard'))
        self.assertContains(follow_response, 'Portal Eunoia')

    @override_settings(
        ALLOWED_HOSTS=['pilateseunoia.com'],
        CSRF_TRUSTED_ORIGINS=build_csrf_trusted_origins(['pilateseunoia.com']),
    )
    def test_login_accepts_https_origin_for_allowed_host_when_proxy_reports_http(self):
        user = self.create_student(
            email='csrf-origin-ok@example.com',
            password='TempLogin2026!',
            must_change_password=False,
        )

        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse('login'), HTTP_HOST='pilateseunoia.com')
        csrf_token = re.search(
            'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        ).group(1)

        post_response = client.post(
            reverse('login'),
            {
                'email': user.email,
                'password': 'TempLogin2026!',
                'csrfmiddlewaretoken': csrf_token,
            },
            HTTP_HOST='pilateseunoia.com',
            HTTP_ORIGIN='https://pilateseunoia.com',
        )

        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(post_response.url, reverse('dashboard'))

    def test_student_can_create_own_account_with_activity_and_pending_access(self):
        response = self.client.post(
            reverse('register'),
            {
                'first_name': 'Meli',
                'last_name': 'López',
                'email': 'meli-self-signup@example.com',
                'phone': '1133445566',
                'primary_section': self.section.pk,
                'password1': 'RegistroSeguro2026!',
                'password2': 'RegistroSeguro2026!',
            },
            follow=True,
        )

        user = User.objects.get(email='meli-self-signup@example.com')
        access = user.get_monthly_access_for(self.today)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(user.check_password('RegistroSeguro2026!'))
        self.assertFalse(user.must_change_password)
        self.assertEqual(user.primary_section, self.section)
        self.assertIsNotNone(access)
        self.assertEqual(access.status, MonthlyAccessStatusType.PENDING_PAYMENT)
        self.assertFalse(access.booking_enabled)
        self.assertContains(response, 'Tu cuenta quedó creada.')

    def test_register_rejects_duplicate_email(self):
        self.create_student(
            email='dup-register@example.com',
            password='Duplicada2026!',
            must_change_password=False,
        )

        response = self.client.post(
            reverse('register'),
            {
                'first_name': 'Otra',
                'last_name': 'Alumna',
                'email': 'dup-register@example.com',
                'phone': '',
                'primary_section': self.section.pk,
                'password1': 'RegistroSeguro2026!',
                'password2': 'RegistroSeguro2026!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una cuenta con ese email.')

    def test_register_rejects_password_mismatch(self):
        response = self.client.post(
            reverse('register'),
            {
                'first_name': 'Meli',
                'last_name': 'López',
                'email': 'meli-mismatch@example.com',
                'phone': '1133445566',
                'primary_section': self.section.pk,
                'password1': 'RegistroSeguro2026!',
                'password2': 'OtraClave2026!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Las contraseñas no coinciden.')

    def test_login_rejects_invalid_credentials(self):
        user = self.create_student(
            email='login-invalid@example.com',
            password='TempInvalid2026!',
            must_change_password=False,
        )

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'ClaveIncorrecta2026!'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No pudimos iniciar sesion con esos datos. Revisa email y contrasena.')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_login_rejects_inactive_user(self):
        user = self.create_student(
            email='login-inactive@example.com',
            password='TempInactive2026!',
            must_change_password=False,
        )
        user.is_active = False
        user.save(update_fields=['is_active', 'updated_at'])

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'TempInactive2026!'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Esta cuenta esta inactiva. Contacta al staff para reactivarla.')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_auth_forms_disable_cache_when_rendering_csrf_tokens(self):
        password_change_user = self.create_student(
            email='must-change-cache@example.com',
            password='TempCache2026!',
            must_change_password=True,
        )

        responses = {
            'login': self.client.get(reverse('login')),
            'register': self.client.get(reverse('register')),
        }

        self.client.force_login(password_change_user)
        responses['change_password_required'] = self.client.get(reverse('change-password-required'))

        for name, response in responses.items():
            with self.subTest(view=name):
                self.assertEqual(response.status_code, 200)
                self.assert_never_cache_headers(response)

    def test_login_redirects_to_password_change_when_required(self):
        user = self.create_student(
            email='must-change@example.com',
            password='TempForce2026!',
            must_change_password=True,
        )

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'TempForce2026!'},
        )

        self.assertRedirects(response, reverse('change-password-required'))
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertRedirects(dashboard_response, reverse('change-password-required'))

    def test_password_change_clears_required_reset_flag(self):
        user = self.create_student(
            email='change-ok@example.com',
            password='TempChange2026!',
            must_change_password=True,
        )
        self.client.post(reverse('login'), {'email': user.email, 'password': 'TempChange2026!'})

        response = self.client.post(
            reverse('change-password-required'),
            {'new_password1': 'DefinitivaSegura2026!', 'new_password2': 'DefinitivaSegura2026!'},
        )

        self.assertRedirects(response, reverse('dashboard'))
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)
        self.assertTrue(user.check_password('DefinitivaSegura2026!'))
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, 'Tus clases')

    def test_change_password_view_redirects_when_reset_is_no_longer_required(self):
        user = self.create_student(
            email='normal-access@example.com',
            password='DefinitivaNormal2026!',
            must_change_password=False,
        )

        self.client.post(reverse('login'), {'email': user.email, 'password': 'DefinitivaNormal2026!'})

        dashboard_response = self.client.get(reverse('dashboard'))
        change_password_response = self.client.get(reverse('change-password-required'))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, f'Hola, {user.first_name}')
        self.assertRedirects(change_password_response, reverse('dashboard'))

    def test_staff_login_redirects_to_admin_portal(self):
        staff_user = User.objects.create_user(
            email='staff-login@example.com',
            password='StaffPortal2026!',
            first_name='Grace',
            last_name='Hopper',
            role='admin',
            is_staff=True,
            must_change_password=False,
        )
        staff_user.temporary_password_set_at = None
        staff_user.save(update_fields=['temporary_password_set_at', 'updated_at'])

        response = self.client.post(
            reverse('login'),
            {'email': staff_user.email, 'password': 'StaffPortal2026!'},
        )

        self.assertRedirects(response, reverse('admin-student-list'))

    def test_login_respects_safe_next_url(self):
        user = self.create_student(
            email='login-next@example.com',
            password='LoginNext2026!',
            must_change_password=False,
        )

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'LoginNext2026!', 'next': reverse('agenda')},
        )

        self.assertRedirects(response, reverse('agenda'))

    def test_staff_login_ignores_student_portal_next_url(self):
        staff_user = User.objects.create_user(
            email='staff-next-student@example.com',
            password='StaffNext2026!',
            first_name='Linus',
            last_name='Torvalds',
            role='admin',
            is_staff=True,
            must_change_password=False,
        )
        staff_user.temporary_password_set_at = None
        staff_user.save(update_fields=['temporary_password_set_at', 'updated_at'])

        response = self.client.post(
            reverse('login'),
            {'email': staff_user.email, 'password': 'StaffNext2026!', 'next': reverse('dashboard')},
        )

        self.assertRedirects(response, reverse('admin-student-list'))

    def test_staff_is_redirected_away_from_student_portal_views(self):
        staff_user = User.objects.create_user(
            email='staff-student-portal@example.com',
            password='StaffDirect2026!',
            first_name='Margaret',
            last_name='Hamilton',
            role='admin',
            is_staff=True,
            must_change_password=False,
        )
        self.client.force_login(staff_user)

        for url in (
            reverse('dashboard'),
            reverse('agenda'),
            reverse('my-bookings'),
            reverse('account'),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, reverse('admin-student-list'))

    def test_login_ignores_unsafe_next_url(self):
        user = self.create_student(
            email='login-unsafe-next@example.com',
            password='UnsafeNext2026!',
            must_change_password=False,
        )

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'UnsafeNext2026!', 'next': 'https://evil.example.com/phishing'},
        )

        self.assertRedirects(response, reverse('dashboard'))

    def test_invalid_password_change_keeps_required_reset_flag(self):
        user = self.create_student(
            email='change-invalid@example.com',
            password='TempMismatch2026!',
            must_change_password=True,
        )
        self.client.post(reverse('login'), {'email': user.email, 'password': 'TempMismatch2026!'})

        response = self.client.post(
            reverse('change-password-required'),
            {'new_password1': 'DefinitivaSegura2026!', 'new_password2': 'DistintaSegura2026!'},
        )

        user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Las contrasenas nuevas no coinciden.')
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.check_password('TempMismatch2026!'))

    def test_must_change_password_middleware_blocks_booking_until_password_change(self):
        user = self.create_student(
            email='must-change-block@example.com',
            password='TempBlock2026!',
            must_change_password=True,
        )
        session = self.create_future_session()
        MonthlyAccessStatus.objects.create(
            student=user,
            month=normalize_month_start(session.date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        self.client.force_login(user)

        agenda_response = self.client.get(reverse('agenda'))
        booking_response = self.client.post(reverse('create-booking', args=[session.pk]))

        self.assertRedirects(agenda_response, reverse('change-password-required'))
        self.assertRedirects(booking_response, reverse('change-password-required'))
        self.assertFalse(Booking.objects.filter(session=session, student=user).exists())

    def test_must_change_password_user_can_logout_without_redirect_loop(self):
        user = self.create_student(
            email='must-change-logout@example.com',
            password='TempLogout2026!',
            must_change_password=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('logout'))

        self.assertRedirects(response, reverse('login'))
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertRedirects(dashboard_response, f"{reverse('login')}?next={reverse('dashboard')}")
