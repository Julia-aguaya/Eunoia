from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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

    def test_command_generates_future_slot_sessions_idempotently_with_slot_association(self):
        out = StringIO()

        call_command('generate_class_sessions', '2026-04-06', '2026-04-20', stdout=out)
        call_command('generate_class_sessions', '2026-04-06', '2026-04-20', stdout=out)

        sessions = ClassSession.objects.filter(section=self.section, date__range=(date(2026, 4, 6), date(2026, 4, 20)))
        self.assertEqual(sessions.count(), 3)
        self.assertTrue(all(session.slot_id == self.slot.pk for session in sessions))
        self.assertIn('Created 3 sessions', out.getvalue())
        self.assertIn('Created 0 sessions', out.getvalue())
        self.assertIn('Skipped duplicates: 3', out.getvalue())


class MaintainFixedBookingHorizonCommandTests(TestCase):
    def test_weekly_maintenance_generates_and_repairs_the_same_horizon(self):
        out = StringIO()
        with patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.timezone.localdate',
            return_value=date(2026, 8, 10),
        ), patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.generate_class_sessions',
            return_value=SimpleNamespace(created_count=3, skipped_duplicates=9),
        ) as generate, patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.repair_expected_fixed_bookings',
            return_value=[{'accion': 'CREATED'}, {'accion': 'ALREADY_BOOKED'}],
        ) as repair:
            call_command('maintain_fixed_booking_horizon', '--days-ahead', '42', stdout=out)

        expected_start = date(2026, 8, 10)
        expected_end = date(2026, 9, 20)
        generate.assert_called_once_with(start_date=expected_start, end_date=expected_end)
        repair.assert_called_once_with(start_date=expected_start, end_date=expected_end, apply=True)
        self.assertIn('start=2026-08-10 end=2026-09-20', out.getvalue())
        self.assertIn('CREATED=1', out.getvalue())

    def test_maintenance_records_capacity_conflicts_and_fails_closed(self):
        session = MagicMock(pk=17)
        assessment = MagicMock()
        out = StringIO()
        with patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.timezone.localdate',
            return_value=date(2026, 8, 10),
        ), patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.generate_class_sessions',
            return_value=SimpleNamespace(created_count=0, skipped_duplicates=1),
        ), patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.repair_expected_fixed_bookings',
            return_value=[{'accion': 'SKIP_CAPACITY', 'session_id': 17}],
        ), patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.ClassSession.objects.get',
            return_value=session,
        ), patch(
            'scheduling.management.commands.maintain_fixed_booking_horizon.assess_fixed_capacity',
            return_value=assessment,
        ), patch('scheduling.management.commands.maintain_fixed_booking_horizon.record_fixed_capacity_conflict') as record:
            with self.assertRaisesMessage(CommandError, 'unresolved_conflicts=1'):
                call_command('maintain_fixed_booking_horizon', stdout=out)

        record.assert_called_once()


class AuditInactiveMonthlyPlansCommandTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.inactive_student = User.objects.create_user(
            email='inactive-plan@example.com', password='StudentPass2026!',
            first_name='Ada', last_name='Inactive', primary_section=self.section,
        )
        self.active_student = User.objects.create_user(
            email='active-plan@example.com', password='StudentPass2026!',
            first_name='Grace', last_name='Active', primary_section=self.section,
        )
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section, weekday=Weekday.MONDAY,
            start_time=time(9), end_time=time(10), is_active=True,
        )
        self.plan = StudentMonthlyPlan.objects.create(
            student=self.inactive_student, month=date(2026, 8, 1), section=self.section,
        )
        self.plan.assign_weekly_slots([self.slot])
        MonthlyAccessStatus.objects.create(
            student=self.inactive_student, month=date(2026, 8, 1),
            status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )
        MonthlyAccessStatus.objects.create(
            student=self.active_student, month=date(2026, 8, 1),
            status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )
        self.past_session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 2), start_time=time(9), end_time=time(10), capacity=4,
        )
        self.future_session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 10), start_time=time(9), end_time=time(10), capacity=4,
        )
        self.past_booking = Booking.objects.create(
            session=self.past_session, student=self.inactive_student, status=BookingStatus.BOOKED,
        )
        self.future_booking = Booking.objects.create(
            session=self.future_session, student=self.inactive_student, status=BookingStatus.BOOKED,
        )
        MonthlyAccessStatus.objects.filter(student=self.inactive_student, month=date(2026, 8, 1)).update(
            status=MonthlyAccessStatusType.SUSPENDED,
            booking_enabled=False,
        )

    def test_dry_run_reports_legacy_inactive_plan_without_writing(self):
        out, err = StringIO(), StringIO()
        call_command('audit_inactive_monthly_plans', '--from-date', '2026-08-05', '--dry-run', stdout=out, stderr=err)

        self.plan.refresh_from_db()
        self.future_booking.refresh_from_db()
        self.assertTrue(self.plan.is_active)
        self.assertEqual(self.future_booking.status, BookingStatus.BOOKED)
        self.assertIn('Ada Inactive', out.getvalue())
        self.assertIn('WOULD_MASK_PLAN_AND_CANCEL_FUTURE_BOOKINGS', out.getvalue())
        self.assertIn('mode=dry-run candidates=1 applied=0', err.getvalue())

    def test_apply_masks_plan_preserves_history_and_is_idempotent(self):
        first_err, second_err = StringIO(), StringIO()
        call_command('audit_inactive_monthly_plans', '--from-date', '2026-08-05', '--apply', stderr=first_err)
        call_command('audit_inactive_monthly_plans', '--from-date', '2026-08-05', '--apply', stderr=second_err)

        self.plan.refresh_from_db()
        self.past_booking.refresh_from_db()
        self.future_booking.refresh_from_db()
        self.assertFalse(self.plan.is_active)
        self.assertEqual(self.plan.plan_slots.count(), 1)
        self.assertEqual(self.past_booking.status, BookingStatus.BOOKED)
        self.assertEqual(self.future_booking.status, BookingStatus.CANCELLED)
        self.assertEqual(self.future_booking.cancellation_reason, BookingCancellationReason.GLOBAL_DEACTIVATION)
        self.assertTrue(self.active_student.is_active)
        self.assertIn('mode=apply candidates=1 applied=1', first_err.getvalue())
        self.assertIn('mode=apply candidates=0 applied=0', second_err.getvalue())

    def test_apply_masks_every_active_plan_for_suspended_student_once(self):
        # Mirrors legacy students with a stale history plus several section/month
        # overrides: the audit must not leave a hidden effective plan behind.
        reformer = Section.objects.get(code='reformer_arriba')
        historical_plan = StudentMonthlyPlan.objects.create(
            student=self.inactive_student, month=date(2026, 5, 1), section=self.section,
        )
        historical_plan.assign_weekly_slots([self.slot])
        reformer_slot = WeeklyClassSlot.objects.create(
            section=reformer, weekday=Weekday.WEDNESDAY, start_time=time(18), end_time=time(19), is_active=True,
        )
        current_reformer_plan = StudentMonthlyPlan.objects.create(
            student=self.inactive_student, month=date(2026, 8, 1), section=reformer,
        )
        current_reformer_plan.assign_weekly_slots([reformer_slot])
        future_plan = StudentMonthlyPlan.objects.create(
            student=self.inactive_student, month=date(2026, 9, 1), section=self.section,
        )
        future_plan.assign_weekly_slots([self.slot])

        first_out, first_err = StringIO(), StringIO()
        second_out, second_err = StringIO(), StringIO()
        call_command('audit_inactive_monthly_plans', '--from-date', '2026-08-05', '--apply', stdout=first_out, stderr=first_err)
        call_command('audit_inactive_monthly_plans', '--from-date', '2026-08-05', '--apply', stdout=second_out, stderr=second_err)

        plan_ids = {self.plan.pk, historical_plan.pk, current_reformer_plan.pk, future_plan.pk}
        self.assertEqual(
            StudentMonthlyPlan.objects.filter(pk__in=plan_ids, is_active=True).count(),
            0,
        )
        self.assertEqual(StudentMonthlyPlan.objects.filter(pk__in=plan_ids).count(), 4)
        self.assertEqual(StudentMonthlyPlanSlot.objects.filter(monthly_plan_id__in=plan_ids).count(), 4)
        self.assertFalse(self.inactive_student.get_effective_monthly_plans_for(date(2026, 9, 1)))
        self.assertEqual(first_out.getvalue().count('MASKED_PLAN_AND_CANCELLED_FUTURE_BOOKINGS'), 4)
        self.assertEqual(second_out.getvalue().splitlines(), [
            'student_id,student_name,access_status,plan_id,plan_month,section,slot_details,future_booking_ids,action',
        ])
        self.assertIn('mode=apply candidates=1 applied=1', first_err.getvalue())
        self.assertIn('mode=apply candidates=0 applied=0', second_err.getvalue())


class RolloverMonthlyAccessStatusesCommandTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.TUESDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            starts_on=date(2026, 8, 1),
        )
        self.student = User.objects.create_user(
            email='rollover-student@example.com',
            password='StudentPass2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=date(2026, 8, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        self.plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=date(2026, 8, 1),
            section=self.section,
        )
        self.plan.assign_weekly_slots([self.slot])

    def test_command_rolls_august_access_into_september_without_touching_plans_or_slots(self):
        out = StringIO()

        call_command('rollover_monthly_access_statuses', '--month', '2026-09', stdout=out)
        call_command('rollover_monthly_access_statuses', '--month', '2026-09', stdout=out)

        access = self.student.get_monthly_access_for(date(2026, 9, 1))
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertEqual(MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 9, 1)).count(), 1)
        self.assertEqual(StudentMonthlyPlan.objects.filter(student=self.student).count(), 1)
        self.assertEqual(self.plan.plan_slots.count(), 1)
        self.assertIn(
            'month=2026-09; students evaluated=1; accesses created=1; '
            'existing accesses=0; skipped due to global deactivation=0; errors/failures=0',
            out.getvalue(),
        )
        self.assertIn(
            'month=2026-09; students evaluated=1; accesses created=0; '
            'existing accesses=1; skipped due to global deactivation=0; errors/failures=0',
            out.getvalue(),
        )

    def test_command_creates_access_for_active_student_without_prior_access(self):
        student = User.objects.create_user(
            email='rollover-no-prior@example.com', password='StudentPass2026!', first_name='Grace', last_name='Hopper',
            primary_section=self.section,
        )

        call_command('rollover_monthly_access_statuses', '--month', '2026-09')

        access = student.get_monthly_access_for(date(2026, 9, 1))
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)

    def test_command_rollover_never_writes_user_auth_state(self):
        with patch.object(User, 'save') as user_save:
            call_command('rollover_monthly_access_statuses', '--month', '2026-09')

        user_save.assert_not_called()
        self.assertTrue(MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 9, 1)).exists())

    def test_command_is_idempotent_and_preserves_manually_suspended_target_access(self):
        target_access = MonthlyAccessStatus.objects.create(
            student=self.student,
            month=date(2026, 9, 1),
            status=MonthlyAccessStatusType.SUSPENDED,
            booking_enabled=False,
        )
        out = StringIO()

        call_command('rollover_monthly_access_statuses', '--month', '2026-09', stdout=out)
        call_command('rollover_monthly_access_statuses', '--month', '2026-09', stdout=out)

        target_access.refresh_from_db()
        self.assertEqual(MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 9, 1)).count(), 1)
        self.assertEqual(target_access.status, MonthlyAccessStatusType.SUSPENDED)
        self.assertFalse(target_access.booking_enabled)
        self.assertIn('accesses created=0; existing accesses=1', out.getvalue())

    def test_command_reenables_next_month_after_monthly_nonpayment_and_generates_booking(self):
        august_access = self.student.get_monthly_access_for(date(2026, 8, 1))
        august_access.suspend_operational_access()

        call_command('rollover_monthly_access_statuses', '--month', '2026-09')
        generate_class_sessions(start_date=date(2026, 9, 1), end_date=date(2026, 9, 1))

        session = ClassSession.objects.get(date=date(2026, 9, 1), start_time=time(9, 0))
        self.assertTrue(Booking.objects.filter(session=session, student=self.student, status=BookingStatus.BOOKED).exists())

    def test_command_does_not_roll_over_globally_deactivated_student(self):
        deactivate_student_globally(student=self.student)
        out = StringIO()

        call_command('rollover_monthly_access_statuses', '--month', '2026-09', stdout=out)

        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertFalse(MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 9, 1)).exists())
        self.assertIn(
            'students evaluated=1; accesses created=0; existing accesses=0; '
            'skipped due to global deactivation=1; errors/failures=0',
            out.getvalue(),
        )

    def test_command_does_not_reactivate_monthly_suspended_student(self):
        suspend_student_monthly_access(
            student=self.student, month=date(2026, 8, 1), synchronize_global_auth=True,
        )

        call_command('rollover_monthly_access_statuses', '--month', '2026-09')

        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertFalse(MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 9, 1)).exists())

    def test_command_reports_individual_partial_failures_and_exits_nonzero(self):
        failing_student = User.objects.create_user(
            email='rollover-fails@example.com', password='StudentPass2026!', first_name='Grace', last_name='Hopper',
            primary_section=self.section,
        )
        out = StringIO()
        err = StringIO()
        original_create = MonthlyAccessStatus.objects.create

        def create_or_fail(**kwargs):
            if kwargs['student'].pk == failing_student.pk:
                raise RuntimeError('database unavailable')
            return original_create(**kwargs)

        with mock.patch(
            'scheduling.use_cases.MonthlyAccessStatus.objects.create',
            side_effect=create_or_fail,
        ):
            with self.assertRaisesMessage(CommandError, 'partial failures'):
                call_command('rollover_monthly_access_statuses', '--month', '2026-09', stdout=out, stderr=err)

        self.assertEqual(out.getvalue(), '')
        self.assertIn(
            f'month=2026-09; student_id={failing_student.pk}; error=database unavailable',
            err.getvalue(),
        )
        self.assertIn(
            'month=2026-09; students evaluated=2; accesses created=1; existing accesses=0; '
            'skipped due to global deactivation=0; errors/failures=1. Rollover completed with failures.',
            err.getvalue(),
        )

    def test_command_requires_valid_month(self):
        with self.assertRaises(CommandError):
            call_command('rollover_monthly_access_statuses')
        with self.assertRaises(CommandError):
            call_command('rollover_monthly_access_statuses', '--month', '2026-9')

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
