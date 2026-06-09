from ._shared import *

class GenerateClassSessionsCommandTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.section.default_capacity = 8
        self.section.save(update_fields=['default_capacity', 'updated_at'])
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=None,
            starts_on=date(2026, 4, 1),
            is_active=True,
        )

    def test_command_generates_sessions_and_skips_duplicates(self):
        existing_session = self.slot.build_session_for_date(date(2026, 4, 6))
        existing_session.save()
        out = StringIO()

        call_command('generate_class_sessions', '2026-04-01', '2026-04-14', stdout=out)

        self.assertEqual(ClassSession.objects.count(), 2)
        self.assertTrue(
            ClassSession.objects.filter(
                section=self.section,
                date=date(2026, 4, 13),
                start_time=time(9, 0),
            ).exists()
        )
        self.assertIn('Created 1 sessions', out.getvalue())
        self.assertIn('Skipped duplicates: 1', out.getvalue())

    def test_command_marks_holiday_closure_sessions(self):
        holiday = HolidayClosure.objects.create(date=date(2026, 4, 6), reason='Feriado')

        call_command('generate_class_sessions', '2026-04-06', '2026-04-06')

        session = ClassSession.objects.get()
        self.assertEqual(session.holiday_closure, holiday)
        self.assertEqual(session.status, SessionStatus.HOLIDAY_CLOSED)

class TemporaryPasswordCommandTests(TestCase):
    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='CommandTemp2026!')
    def test_command_updates_explicit_users_with_default_password(self):
        first_user = User.objects.create_user(
            email='first@example.com',
            password='secret123',
            first_name='First',
            last_name='Student',
        )
        second_user = User.objects.create_user(
            email='second@example.com',
            password='secret123',
            first_name='Second',
            last_name='Student',
        )
        out = StringIO()

        call_command('set_temporary_password', 'first@example.com', 'second@example.com', stdout=out)

        first_user.refresh_from_db()
        second_user.refresh_from_db()
        self.assertTrue(first_user.check_password('CommandTemp2026!'))
        self.assertTrue(second_user.check_password('CommandTemp2026!'))
        self.assertTrue(first_user.must_change_password)
        self.assertTrue(second_user.must_change_password)
        self.assertIn('Temporary password assigned to 2 users', out.getvalue())

    def test_command_can_target_all_students(self):
        student = User.objects.create_user(
            email='student-all@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            role='student',
        )
        admin_user = User.objects.create_user(
            email='admin-all@example.com',
            password='secret123',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True,
        )

        call_command('set_temporary_password', '--all-students', '--password', 'BulkTemp2026!')

        student.refresh_from_db()
        admin_user.refresh_from_db()
        self.assertTrue(student.check_password('BulkTemp2026!'))
        self.assertFalse(admin_user.check_password('BulkTemp2026!'))

class BootstrapEunoiaCommandTests(TestCase):
    def test_command_creates_admin_and_restores_base_sections(self):
        Section.objects.all().delete()
        out = StringIO()

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            'ops@example.com',
            '--admin-password',
            'BootstrapAdmin2026!',
            '--admin-first-name',
            'Ops',
            '--admin-last-name',
            'Lead',
            stdout=out,
        )

        admin_user = User.objects.get(email='ops@example.com')
        self.assertEqual(Section.objects.count(), 3)
        self.assertEqual(admin_user.first_name, 'Ops')
        self.assertEqual(admin_user.last_name, 'Lead')
        self.assertEqual(admin_user.role, 'admin')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
        self.assertFalse(admin_user.must_change_password)
        self.assertTrue(admin_user.check_password('BootstrapAdmin2026!'))
        self.assertIn('Bootstrap ready', out.getvalue())

    def test_command_updates_existing_admin_without_resetting_password_by_default(self):
        admin_user = User.objects.create_user(
            email='ops-existing@example.com',
            password='OriginalAdmin2026!',
            first_name='Old',
            last_name='Name',
            role='student',
            is_staff=False,
            must_change_password=True,
        )

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            admin_user.email,
            '--admin-password',
            'NewAdmin2026!',
            '--admin-first-name',
            'New',
            '--admin-last-name',
            'Owner',
        )

        admin_user.refresh_from_db()
        self.assertEqual(admin_user.first_name, 'New')
        self.assertEqual(admin_user.last_name, 'Owner')
        self.assertEqual(admin_user.role, 'admin')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertFalse(admin_user.must_change_password)
        self.assertTrue(admin_user.check_password('OriginalAdmin2026!'))
        self.assertFalse(admin_user.check_password('NewAdmin2026!'))

    def test_command_can_reset_existing_admin_password(self):
        admin_user = User.objects.create_user(
            email='ops-reset@example.com',
            password='OriginalAdmin2026!',
            first_name='Ops',
            last_name='Reset',
            role='admin',
            is_staff=True,
            must_change_password=False,
        )

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            admin_user.email,
            '--admin-password',
            'ResetAdmin2026!',
            '--reset-password',
        )

        admin_user.refresh_from_db()
        self.assertTrue(admin_user.check_password('ResetAdmin2026!'))
        self.assertFalse(admin_user.must_change_password)

    def test_command_can_seed_demo_slots_and_generate_upcoming_sessions(self):
        out = StringIO()

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            'ops-demo@example.com',
            '--admin-password',
            'BootstrapAdmin2026!',
            '--with-demo-slots',
            '--generate-next-days',
            '14',
            stdout=out,
        )

        self.assertEqual(WeeklyClassSlot.objects.count(), 6)
        self.assertGreater(ClassSession.objects.count(), 0)
        self.assertIn('demo slots created: 6', out.getvalue())
        self.assertIn('sessions generated:', out.getvalue())

class EunoiaReadinessCommandTests(TestCase):
    def test_command_reports_ok_when_minimum_data_exists(self):
        section = Section.objects.get(code='cadillac')
        User.objects.create_user(
            email='ops-ready@example.com',
            password='ReadyAdmin2026!',
            first_name='Ops',
            last_name='Ready',
            role='admin',
            is_staff=True,
        )
        WeeklyClassSlot.objects.create(
            section=section,
            weekday=Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_active=True,
        )
        out = StringIO()

        call_command('check_eunoia_readiness', '--strict', stdout=out)

        self.assertIn('Readiness check: OK', out.getvalue())
        self.assertIn('weekly_slots_active=1', out.getvalue())

    def test_command_fails_in_strict_mode_without_schedule_data(self):
        User.objects.create_user(
            email='ops-missing@example.com',
            password='ReadyAdmin2026!',
            first_name='Ops',
            last_name='Missing',
            role='admin',
            is_staff=True,
        )

        with self.assertRaises(CommandError):
            call_command('check_eunoia_readiness', '--strict')

class DemoSeedCommandTests(TestCase):
    def test_demo_seed_command_creates_repeatable_demo_data(self):
        out = StringIO()

        call_command('seed_demo_eunoia', stdout=out)

        self.assertTrue(User.objects.get(email=DEMO_ADMIN_EMAIL).check_password('DemoAdmin2026!'))
        self.assertTrue(User.objects.get(email=DEMO_STAFF_EMAIL).check_password('DemoStaff2026!'))
        self.assertEqual(User.objects.filter(role='student', email__endswith='.demo@example.com').count(), 6)
        self.assertEqual(WeeklyClassSlot.objects.filter(is_active=True).count(), 6)
        self.assertGreater(ClassSession.objects.filter(status=SessionStatus.SCHEDULED).count(), 0)

        ada = User.objects.get(email='ada.demo@example.com')
        bea = User.objects.get(email='bea.demo@example.com')
        clara = User.objects.get(email='clara.demo@example.com')
        dora = User.objects.get(email='dora.demo@example.com')
        eva = User.objects.get(email='eva.demo@example.com')
        current_month = normalize_month_start(timezone.localdate())

        self.assertEqual(
            ada.monthly_access_statuses.get(month=current_month).status,
            MonthlyAccessStatusType.ACTIVE,
        )
        self.assertEqual(
            bea.monthly_access_statuses.get(month=current_month).status,
            MonthlyAccessStatusType.PENDING_PAYMENT,
        )
        self.assertEqual(
            clara.monthly_access_statuses.get(month=current_month).status,
            MonthlyAccessStatusType.SUSPENDED,
        )
        self.assertTrue(
            Booking.objects.filter(student=ada, status=BookingStatus.BOOKED).exists()
        )
        self.assertTrue(
            Booking.objects.filter(student=dora, status=BookingStatus.BOOKED, source='makeup').exists()
        )
        self.assertTrue(
            RecoveryCredit.objects.filter(student=eva, status=RecoveryCreditStatus.AVAILABLE).exists()
        )
        self.assertTrue(User.objects.get(email='sofia.demo@example.com').check_password(DEMO_STUDENT_PASSWORD))
        self.assertIn('Demo ready', out.getvalue())

class DemoSmokeCommandTests(TestCase):
    def test_demo_smoke_command_passes_against_seeded_data(self):
        call_command('seed_demo_eunoia')
        original_booking_count = Booking.objects.count()
        original_recovery_count = RecoveryCredit.objects.count()
        out = StringIO()

        call_command('smoke_test_eunoia_demo', stdout=out)

        self.assertIn('Demo smoke test: OK', out.getvalue())
        self.assertEqual(Booking.objects.count(), original_booking_count)
        self.assertEqual(RecoveryCredit.objects.count(), original_recovery_count)
