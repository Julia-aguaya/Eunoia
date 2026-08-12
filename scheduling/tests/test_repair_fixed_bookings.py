from datetime import date, time
import inspect
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone

from scheduling import fixed_booking_repair
from scheduling import fixed_booking_history

from ._shared import (
    Booking,
    BookingSource,
    BookingStatus,
    ClassSession,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    Section,
    SessionStatus,
    StudentMonthlyPlan,
    TestCase,
    User,
    WeeklyClassSlot,
    normalize_month_start,
)


class RepairFixedBookingsCommandTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.student = User.objects.create_user(
            email='repair-student@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section,
        )
        self.session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 5), start_time=time(9), end_time=time(10),
            capacity=2, status=SessionStatus.SCHEDULED,
        )
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section, weekday=self.session.date.isoweekday(), start_time=self.session.start_time,
            end_time=self.session.end_time, is_active=True,
        )
        self.session.slot = self.slot
        self.session.save(update_fields=['slot', 'updated_at'])
        StudentMonthlyPlan.objects.create(
            student=self.student, month=normalize_month_start(self.session.date), section=self.section,
        ).assign_weekly_slots([self.slot])
        MonthlyAccessStatus.objects.create(
            student=self.student, month=normalize_month_start(self.session.date),
            status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )

    def run_command(self, *extra):
        stdout = StringIO()
        stderr = StringIO()
        call_command(
            'repair_fixed_bookings', '--start-date', '2026-08-05', '--end-date', '2026-08-05',
            *extra, stdout=stdout, stderr=stderr,
        )
        return stdout.getvalue(), stderr.getvalue()

    def create_second_eligible_student(self):
        student = User.objects.create_user(
            email='repair-second-capacity@example.com', password='secret123', first_name='Grace', last_name='Hopper',
            primary_section=self.section,
        )
        StudentMonthlyPlan.objects.create(
            student=student, month=normalize_month_start(self.session.date), section=self.section,
        ).assign_weekly_slots([self.slot])
        MonthlyAccessStatus.objects.create(
            student=student, month=normalize_month_start(self.session.date),
            status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )
        return student

    def test_dry_run_never_booked_does_not_enter_atomic_or_lock(self):
        audit_row = {
            'student_id': 1, 'nombre': 'Ada Lovelace', 'session_id': 2,
            'fecha': '2026-08-05', 'hora': '09:00', 'section': 'cadillac',
            'clasificacion': 'D_never_booked',
        }
        session_manager = MagicMock()
        booking_manager = MagicMock()
        user_manager = MagicMock()
        session_manager.get.return_value = MagicMock(pk=2, capacity=1)
        booking_manager.filter.return_value.count.return_value = 0
        mysql_connection = MagicMock(vendor='mysql')

        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=[audit_row]), \
              patch.object(fixed_booking_repair.ClassSession, 'objects', session_manager), \
              patch.object(fixed_booking_repair.Booking, 'objects', booking_manager), \
              patch.object(fixed_booking_repair.User, 'objects', user_manager), \
              patch.object(fixed_booking_repair, 'connection', mysql_connection), \
              patch.object(fixed_booking_repair.transaction, 'atomic') as atomic:
            fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), apply=False,
            )

        atomic.assert_not_called()
        session_manager.select_for_update.assert_not_called()
        booking_manager.select_for_update.assert_not_called()
        mysql_connection.close.assert_not_called()
        mysql_connection.ensure_connection.assert_not_called()

    def test_apply_history_locks_session_and_bookings(self):
        audit_row = {
            'student_id': 1, 'nombre': 'Ada Lovelace', 'session_id': 2,
            'fecha': '2026-08-05', 'hora': '09:00', 'section': 'cadillac',
            'clasificacion': 'C_history_present',
        }
        session = MagicMock(id=2, pk=2)
        student = MagicMock(id=1, pk=1, is_active=True)
        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=[audit_row]), \
              patch.object(fixed_booking_repair, 'materialize_fixed_booking_lock_context', return_value={}), \
              patch.object(fixed_booking_repair, 'lock_fixed_booking_context', return_value=(student, session, [], None, [], [], [])) as lock, \
               patch.object(fixed_booking_repair, 'fixed_booking_context_is_eligible_locked', return_value=True), \
              patch.object(fixed_booking_repair, '_history_decision', return_value=('HISTORY_PRESENT', 'history')):
            fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), apply=True,
            )

        lock.assert_called_once_with(lock_context={})

    def test_apply_rechecks_current_eligibility_without_running_audit_under_lock(self):
        audit_row = {
            'student_id': 1, 'nombre': 'Ada Lovelace', 'session_id': 2,
            'fecha': '2026-08-05', 'hora': '09:00', 'section': 'cadillac',
            'clasificacion': 'D_never_booked',
        }
        session = MagicMock(id=2, pk=2, date=date(2026, 8, 5))
        student = MagicMock(id=1, pk=1, is_active=True)
        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=[audit_row]) as audit, \
              patch.object(fixed_booking_repair, 'materialize_fixed_booking_lock_context', return_value={}), \
              patch.object(fixed_booking_repair, 'lock_fixed_booking_context', return_value=(student, session, [], None, [], [], [])), \
                patch.object(fixed_booking_repair, 'fixed_booking_context_is_eligible_locked', return_value=False):
            results = fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), apply=True,
            )

        self.assertEqual(audit.call_count, 1)
        self.assertEqual(results[0]['accion'], 'SKIP_NOT_ELIGIBLE')

    def test_apply_enters_a_separate_atomic_block_for_each_candidate(self):
        audit_rows = [
            {
                'student_id': student_id, 'nombre': 'Ada Lovelace', 'session_id': 2,
                'fecha': '2026-08-05', 'hora': '09:00', 'section': 'cadillac',
                'clasificacion': 'C_history_present',
            }
            for student_id in (1, 3)
        ]
        session = MagicMock(id=2, pk=2, date=date(2026, 8, 5))
        student = MagicMock(id=1, pk=1, is_active=True)
        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=audit_rows), \
               patch.object(fixed_booking_repair, 'materialize_fixed_booking_lock_context', return_value={}), \
               patch.object(fixed_booking_repair, 'lock_fixed_booking_context', return_value=(student, session, [], None, [], [], [])), \
                 patch.object(fixed_booking_repair, 'fixed_booking_context_is_eligible_locked', return_value=True), \
               patch.object(fixed_booking_repair, '_history_decision', return_value=('HISTORY_PRESENT', 'history')), \
                patch.object(fixed_booking_repair.transaction, 'atomic') as atomic:
            fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), apply=True,
            )

        self.assertEqual(atomic.call_count, 2)

    def test_apply_never_runs_relationship_heavy_audit_inside_lock(self):
        audit_row = {
            'student_id': self.student.pk, 'nombre': 'Ada Lovelace', 'session_id': self.session.pk,
            'fecha': '2026-08-05', 'hora': '09:00', 'section': 'cadillac',
            'clasificacion': 'D_never_booked',
        }

        locked = False

        def audit_before_lock(**kwargs):
            self.assertFalse(locked, 'audit must complete before lock acquisition')
            return [audit_row]

        def mark_lock(*, lock_context):
            nonlocal locked
            locked = True
            return original_lock(lock_context=lock_context)

        original_lock = fixed_booking_repair.lock_fixed_booking_context
        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', side_effect=audit_before_lock) as audit, \
             patch.object(fixed_booking_repair, 'lock_fixed_booking_context', side_effect=mark_lock):
            fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date,
                end_date=self.session.date,
                apply=True,
            )

        audit.assert_called_once_with(start_date=self.session.date, end_date=self.session.date)

    def test_locked_revalidation_and_writes_do_not_traverse_relations(self):
        locked_eligibility = inspect.getsource(fixed_booking_history.fixed_booking_context_is_eligible_locked)
        lock_context = inspect.getsource(fixed_booking_history.lock_fixed_booking_context)
        direct_write = inspect.getsource(Booking.objects.create_fixed_booking_while_locked)
        technical_restore = inspect.getsource(fixed_booking_history._restore_fixed_booking)

        for source in (locked_eligibility, lock_context, direct_write, technical_restore):
            self.assertNotIn('select_related', source)
            self.assertNotIn('prefetch_related', source)
            self.assertNotIn('full_clean', source)
        self.assertNotIn('__', locked_eligibility)
        self.assertNotIn('weekly_class_slot__', lock_context)
        self.assertNotIn('.save(', direct_write)
        self.assertNotIn('.save(', technical_restore)

    def test_apply_creates_with_locked_direct_write_without_booking_full_clean(self):
        audit_row = next(fixed_booking_repair.audit_expected_fixed_bookings(
            start_date=self.session.date,
            end_date=self.session.date,
        ))

        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=[audit_row]), \
             patch.object(Booking, 'full_clean', side_effect=AssertionError('must not validate through relations')):
            results = fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date, end_date=self.session.date, apply=True,
            )

        self.assertEqual(results[0]['accion'], 'CREATED')
        self.assertTrue(Booking.objects.filter(session=self.session, student=self.student).exists())

    def test_apply_restores_with_locked_direct_write_without_booking_full_clean(self):
        booking = Booking.objects.create_booking(session=self.session, student=self.student)
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancelled_by=None,
            cancellation_generates_recovery=False,
        )
        audit_row = next(fixed_booking_repair.audit_expected_fixed_bookings(
            start_date=self.session.date,
            end_date=self.session.date,
        ))

        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=[audit_row]), \
             patch.object(Booking, 'full_clean', side_effect=AssertionError('must not validate through relations')):
            results = fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date, end_date=self.session.date, apply=True,
            )

        booking.refresh_from_db()
        self.assertEqual(results[0]['accion'], 'RESTORED')
        self.assertEqual(booking.status, BookingStatus.BOOKED)

    def test_apply_rechecks_current_plan_slot_before_creating(self):
        audit_row = next(fixed_booking_repair.audit_expected_fixed_bookings(
            start_date=self.session.date,
            end_date=self.session.date,
        ))
        self.student.monthly_plans.get().plan_slots.all().delete()

        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=[audit_row]):
            results = fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date,
                end_date=self.session.date,
                apply=True,
            )

        self.assertEqual(results[0]['accion'], 'SKIP_NOT_ELIGIBLE')
        self.assertFalse(Booking.objects.filter(session=self.session, student=self.student).exists())

    def test_apply_rechecks_current_plan_slot_before_restoring_history(self):
        booking = Booking.objects.create_booking(
            session=self.session,
            student=self.student,
            source=BookingSource.FIXED_SLOT,
        )
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancelled_by=None,
            cancellation_generates_recovery=False,
        )
        audit_row = next(fixed_booking_repair.audit_expected_fixed_bookings(
            start_date=self.session.date,
            end_date=self.session.date,
        ))
        self.student.monthly_plans.get().plan_slots.all().delete()

        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', return_value=[audit_row]):
            results = fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date,
                end_date=self.session.date,
                apply=True,
            )

        booking.refresh_from_db()
        self.assertEqual(results[0]['accion'], 'SKIP_NOT_ELIGIBLE')
        self.assertEqual(booking.status, BookingStatus.CANCELLED)


    def test_dry_run_is_default_and_does_not_write(self):
        stdout, stderr = self.run_command()

        self.assertEqual(Booking.objects.count(), 0)
        self.assertIn('WOULD_CREATE', stdout)
        self.assertIn('modo', stdout)
        self.assertIn('mode=dry-run', stderr)

    def test_apply_creates_missing_booking_and_is_idempotent(self):
        first_stdout, first_stderr = self.run_command('--apply')
        second_stdout, second_stderr = self.run_command('--apply')

        self.assertEqual(Booking.objects.filter(session=self.session, student=self.student).count(), 1)
        self.assertIn('CREATED', first_stdout)
        self.assertIn('ALREADY_BOOKED', second_stdout)
        self.assertIn('mode=apply', first_stderr)
        self.assertIn('mode=apply', second_stderr)

    def test_repair_does_not_recreate_booking_for_globally_inactive_student(self):
        self.student.is_active = False
        self.student.save(update_fields=['is_active', 'updated_at'])

        stdout, _ = self.run_command('--apply')

        self.assertFalse(Booking.objects.filter(student=self.student).exists())
        self.assertNotIn('CREATED', stdout)

    def test_booked_pair_is_not_duplicated(self):
        Booking.objects.create_booking(session=self.session, student=self.student)

        stdout, _ = self.run_command('--apply')

        self.assertEqual(Booking.objects.filter(session=self.session, student=self.student).count(), 1)
        self.assertIn('ALREADY_BOOKED', stdout)

    def test_self_cancelled_fixed_slot_is_respected_even_with_recovery(self):
        booking = Booking.objects.create_booking(session=self.session, student=self.student)
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancelled_by=self.student,
            cancellation_generates_recovery=True,
        )

        stdout, _ = self.run_command('--apply')

        self.assertEqual(Booking.objects.filter(session=self.session, student=self.student).count(), 1)
        self.assertFalse(Booking.objects.filter(session=self.session, status=BookingStatus.BOOKED).exists())
        self.assertIn('RESPECT_CANCELLED', stdout)

    def test_restores_eligible_technical_cancellation_preserving_booking_identity(self):
        booking = Booking.objects.create_booking(
            session=self.session,
            student=self.student,
            source=BookingSource.FIXED_SLOT,
        )
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancelled_by=None,
            cancellation_generates_recovery=False,
        )

        dry_run_stdout, _ = self.run_command()
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        apply_stdout, _ = self.run_command('--apply')
        booking.refresh_from_db()
        second_stdout, _ = self.run_command('--apply')

        self.assertIn('WOULD_RESTORE', dry_run_stdout)
        self.assertEqual(booking.pk, Booking.objects.get(session=self.session, student=self.student).pk)
        self.assertIn('RESTORED', apply_stdout)
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertIsNone(booking.cancelled_at)
        self.assertIsNone(booking.cancelled_by)
        self.assertEqual(Booking.objects.filter(session=self.session, student=self.student).count(), 1)
        self.assertIn('ALREADY_BOOKED', second_stdout)

    def test_repair_never_restores_global_deactivation_history(self):
        booking = Booking.objects.create_booking(session=self.session, student=self.student)
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancellation_reason='global_deactivation',
        )

        stdout, _ = self.run_command('--apply')

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertIn('RESPECT_GLOBAL_DEACTIVATION', stdout)

    def test_repair_does_not_restore_recovery_or_moved_history(self):
        booking = Booking.objects.create_booking(
            session=self.session,
            student=self.student,
            source=BookingSource.FIXED_SLOT,
        )
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancellation_generates_recovery=True,
        )

        recovery_stdout, _ = self.run_command('--apply')
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertIn('HISTORY_PRESENT', recovery_stdout)

        moved_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 8, 6),
            start_time=time(9),
            end_time=time(10),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.filter(pk=booking.pk).update(
            cancellation_generates_recovery=False,
            moved_to_session=moved_session,
        )
        moved_stdout, _ = self.run_command('--apply')
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertIn('HISTORY_PRESENT', moved_stdout)

    def test_out_of_range_session_is_untouched(self):
        self.session.date = date(2026, 8, 6)
        self.session.save(update_fields=['date', 'updated_at'])

        stdout, stderr = self.run_command('--apply')

        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(stdout.splitlines()[0], 'student_id,alumna,session_id,fecha,horario,sección,estado_encontrado,acción,modo,detalle')
        self.assertIn('total=0', stderr)

    def test_apply_skips_full_session(self):
        self.session.capacity = 1
        self.session.save(update_fields=['capacity', 'updated_at'])
        other_student = User.objects.create_user(
            email='repair-other@example.com', password='secret123', first_name='Grace', last_name='Hopper',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=other_student, month=normalize_month_start(self.session.date),
            status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )
        Booking.objects.create_booking(session=self.session, student=other_student, source=BookingSource.FIXED_SLOT)

        stdout, _ = self.run_command('--apply')

        self.assertFalse(Booking.objects.filter(session=self.session, student=self.student).exists())
        self.assertIn('SKIP_CAPACITY', stdout)

    def test_dry_run_projects_capacity_across_multiple_missing_candidates(self):
        self.session.capacity = 1
        self.session.save(update_fields=['capacity', 'updated_at'])
        second_student = self.create_second_eligible_student()

        dry_stdout, dry_stderr = self.run_command()

        self.assertEqual(Booking.objects.count(), 0)
        self.assertIn('WOULD_CREATE=1', dry_stderr)
        self.assertIn('SKIP_CAPACITY=1', dry_stderr)
        self.assertIn(f'{self.student.pk},Ada Lovelace', dry_stdout)
        self.assertIn(f'{second_student.pk},Grace Hopper', dry_stdout)

        apply_stdout, apply_stderr = self.run_command('--apply')

        self.assertIn('CREATED=1', apply_stderr)
        self.assertIn('SKIP_CAPACITY=1', apply_stderr)
        self.assertEqual(Booking.objects.filter(session=self.session, status=BookingStatus.BOOKED).count(), 1)
        self.assertIn('CREATED', apply_stdout)
        self.assertIn('SKIP_CAPACITY', apply_stdout)

    def test_repair_restores_safe_staff_cancellation_without_creating_a_duplicate(self):
        staff = User.objects.create_user(
            email='repair-staff@example.com', password='secret123', first_name='Staff', last_name='Member',
            role='admin', is_staff=True,
        )
        booking = Booking.objects.create_booking(session=self.session, student=self.student, source=BookingSource.FIXED_SLOT)
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancelled_by=staff,
            cancellation_generates_recovery=False,
        )

        dry_stdout, _ = self.run_command()
        apply_stdout, _ = self.run_command('--apply')
        booking.refresh_from_db()

        self.assertIn('WOULD_RESTORE', dry_stdout)
        self.assertIn('RESTORED', apply_stdout)
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertEqual(Booking.objects.filter(session=self.session, student=self.student).count(), 1)


class RepairFixedBookingsTransactionTests(TransactionTestCase):
    def setUp(self):
        self.section, _ = Section.objects.get_or_create(code='cadillac', defaults={'name': 'Cadillac'})
        self.first_student = User.objects.create_user(
            email='repair-first@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section,
        )
        self.second_student = User.objects.create_user(
            email='repair-second@example.com', password='secret123', first_name='Grace', last_name='Hopper',
            primary_section=self.section,
        )
        self.session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 5), start_time=time(9), end_time=time(10),
            capacity=3, status=SessionStatus.SCHEDULED,
        )
        slot = WeeklyClassSlot.objects.create(
            section=self.section, weekday=self.session.date.isoweekday(), start_time=self.session.start_time,
            end_time=self.session.end_time, is_active=True,
        )
        self.session.slot = slot
        self.session.save(update_fields=['slot', 'updated_at'])
        for student in (self.first_student, self.second_student):
            StudentMonthlyPlan.objects.create(
                student=student, month=normalize_month_start(self.session.date), section=self.section,
            ).assign_weekly_slots([slot])
            MonthlyAccessStatus.objects.create(
                student=student, month=normalize_month_start(self.session.date),
                status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
            )

    def test_failure_on_later_candidate_preserves_prior_candidate_and_rerun_is_idempotent(self):
        original_create_booking = Booking.objects.create_fixed_booking_while_locked

        def create_or_fail(*, student, **kwargs):
            if student == self.second_student:
                raise RuntimeError('later candidate failed')
            return original_create_booking(student=student, **kwargs)

        with patch.object(Booking.objects, 'create_fixed_booking_while_locked', side_effect=create_or_fail):
            with self.assertRaisesMessage(RuntimeError, 'later candidate failed'):
                fixed_booking_repair.repair_expected_fixed_bookings(
                    start_date=self.session.date, end_date=self.session.date, apply=True,
                )

        self.assertTrue(Booking.objects.filter(session=self.session, student=self.first_student).exists())
        self.assertFalse(Booking.objects.filter(session=self.session, student=self.second_student).exists())

        fixed_booking_repair.repair_expected_fixed_bookings(
            start_date=self.session.date, end_date=self.session.date, apply=True,
        )

        self.assertEqual(Booking.objects.filter(session=self.session, student=self.first_student).count(), 1)
        self.assertEqual(Booking.objects.filter(session=self.session, student=self.second_student).count(), 1)

    def test_mysql_2013_before_create_retries_with_a_new_transaction(self):
        original_create_booking = Booking.objects.create_fixed_booking_while_locked
        mysql_connection = MagicMock(vendor='mysql')
        attempts = 0

        def create_or_disconnect(**kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise OperationalError(2013, 'lost connection')
            return original_create_booking(**kwargs)

        with patch.object(fixed_booking_repair, 'connection', mysql_connection), \
             patch.object(fixed_booking_repair.time, 'sleep') as sleep, \
              patch.object(Booking.objects, 'create_fixed_booking_while_locked', side_effect=create_or_disconnect):
            results = fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date, end_date=self.session.date, apply=True,
            )

        self.assertEqual(Booking.objects.filter(session=self.session, student=self.first_student).count(), 1)
        self.assertEqual(results[0]['accion'], 'CREATED_AFTER_RETRY')
        mysql_connection.close.assert_called_once_with()
        mysql_connection.ensure_connection.assert_called_once_with()
        sleep.assert_called_once_with(fixed_booking_repair.RETRY_BACKOFF_SECONDS)

    def test_mysql_2013_after_create_recovers_ambiguous_commit_without_recreating(self):
        audit_row = {
            'student_id': 1, 'nombre': 'Ada Lovelace', 'session_id': 2,
            'fecha': '2026-08-05', 'hora': '09:00', 'section': 'cadillac',
            'clasificacion': 'D_never_booked',
        }
        session = MagicMock(id=2, pk=2, date=date(2026, 8, 5))
        student = MagicMock(id=1, pk=1, is_active=True)
        booked = MagicMock(status=BookingStatus.BOOKED)
        booked.student_id = student.pk
        booking_manager = MagicMock()
        first_atomic = MagicMock()
        first_atomic.__exit__.side_effect = OperationalError(2013, 'lost connection during commit')
        mysql_connection = MagicMock(vendor='mysql')

        recovered_audit_row = {**audit_row, 'clasificacion': 'A_booked'}
        with patch.object(fixed_booking_repair, 'audit_expected_fixed_bookings', side_effect=[[audit_row], [recovered_audit_row]]) as audit, \
               patch.object(fixed_booking_repair.Booking, 'objects', booking_manager), \
               patch.object(fixed_booking_repair, 'materialize_fixed_booking_lock_context', return_value={}), \
               patch.object(fixed_booking_repair, 'lock_fixed_booking_context', side_effect=[
                   (student, session, [], None, [], [], []),
                   (student, session, [], None, [], [], [booked]),
               ]), \
                patch.object(fixed_booking_repair, 'fixed_booking_context_is_eligible_locked', return_value=True), \
              patch.object(fixed_booking_repair.transaction, 'atomic', side_effect=[first_atomic, MagicMock()]), \
             patch.object(fixed_booking_repair, 'connection', mysql_connection), \
             patch.object(fixed_booking_repair.time, 'sleep'):
            result = fixed_booking_repair._repair_missing_candidate(audit_row=audit_row, mode='apply')

        self.assertEqual(result['accion'], 'RECOVERED_AFTER_AMBIGUOUS_COMMIT')
        self.assertEqual(booking_manager.create_fixed_booking_while_locked.call_count, 1)
        self.assertEqual(audit.call_count, 0)
        mysql_connection.close.assert_called_once_with()
        mysql_connection.ensure_connection.assert_called_once_with()

    def test_mysql_retry_is_isolated_to_the_failed_candidate(self):
        original_create_booking = Booking.objects.create_fixed_booking_while_locked
        calls = []
        mysql_connection = MagicMock(vendor='mysql')

        def create_or_disconnect(*, student, **kwargs):
            calls.append(student.pk)
            if student == self.first_student and calls.count(student.pk) == 1:
                raise OperationalError(2013, 'lost connection')
            return original_create_booking(student=student, **kwargs)

        with patch.object(fixed_booking_repair, 'connection', mysql_connection), \
             patch.object(fixed_booking_repair.time, 'sleep'), \
              patch.object(Booking.objects, 'create_fixed_booking_while_locked', side_effect=create_or_disconnect):
            results = fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date, end_date=self.session.date, apply=True,
            )

        self.assertEqual([row['accion'] for row in results], ['CREATED_AFTER_RETRY', 'CREATED'])
        self.assertEqual(Booking.objects.filter(session=self.session).count(), 2)
        self.assertEqual(mysql_connection.close.call_count, 1)

    def test_mysql_retry_limit_chains_the_original_operational_error_and_reports_context(self):
        mysql_connection = MagicMock(vendor='mysql')

        with patch.object(fixed_booking_repair, 'connection', mysql_connection), \
             patch.object(fixed_booking_repair.time, 'sleep'), \
              patch.object(Booking.objects, 'create_fixed_booking_while_locked', side_effect=OperationalError(2013, 'lost connection')), \
             self.assertLogs('scheduling.fixed_booking_repair', level='ERROR') as logs:
            with self.assertRaises(fixed_booking_repair.CandidateRepairError) as caught:
                fixed_booking_repair.repair_expected_fixed_bookings(
                    start_date=self.session.date, end_date=self.session.date, apply=True,
                )

        self.assertEqual(mysql_connection.close.call_count, 2)
        self.assertEqual(mysql_connection.ensure_connection.call_count, 2)
        self.assertIsInstance(caught.exception.__cause__, OperationalError)
        self.assertEqual(fixed_booking_repair._mysql_disconnect_errno(caught.exception.__cause__), 2013)
        self.assertIn('attempts=3 pending=True errno=2013', logs.output[0])

    def test_transient_reconnect_failure_does_not_cut_the_three_attempt_budget(self):
        mysql_connection = MagicMock(vendor='mysql')

        with patch.object(fixed_booking_repair, 'connection', mysql_connection), \
             patch.object(fixed_booking_repair.time, 'sleep'), \
              patch.object(Booking.objects, 'create_fixed_booking_while_locked', side_effect=OperationalError(2013, 'lost connection')), \
             self.assertRaises(fixed_booking_repair.CandidateRepairError) as caught:
            mysql_connection.ensure_connection.side_effect = OperationalError(2006, 'server gone away')
            fixed_booking_repair.repair_expected_fixed_bookings(
                start_date=self.session.date, end_date=self.session.date, apply=True,
            )

        self.assertEqual(mysql_connection.close.call_count, 2)
        self.assertEqual(mysql_connection.ensure_connection.call_count, 2)
        self.assertEqual(caught.exception.attempts, 3)
        self.assertEqual(fixed_booking_repair._mysql_disconnect_errno(caught.exception.__cause__), 2013)

    def test_command_reports_pending_candidate_before_reraising(self):
        stdout = StringIO()
        stderr = StringIO()
        original_error = OperationalError(2013, 'lost connection')
        candidate_error = fixed_booking_repair.CandidateRepairError(
            audit_row={
                'student_id': self.first_student.id, 'nombre': 'Ada Lovelace', 'session_id': self.session.id,
                'fecha': '2026-08-05', 'hora': '09:00', 'section': 'cadillac',
                'clasificacion': 'D_never_booked',
            },
            attempts=3,
            errno=2013,
            detail='Se agotaron los reintentos tras una desconexion MySQL: (2013, lost connection).',
        )
        candidate_error.__cause__ = original_error

        with patch('scheduling.management.commands.repair_fixed_bookings.repair_expected_fixed_bookings',
                   side_effect=candidate_error):
            with self.assertRaises(fixed_booking_repair.CandidateRepairError) as caught:
                call_command(
                    'repair_fixed_bookings', '--start-date', '2026-08-05', '--end-date', '2026-08-05', '--apply',
                    stdout=stdout, stderr=stderr,
                )

        self.assertIs(caught.exception.__cause__, original_error)
        self.assertIn(f'student_id={self.first_student.id}', stderr.getvalue())
        self.assertIn(f'session_id={self.session.id}', stderr.getvalue())
        self.assertIn('attempts=3 errno=2013', stderr.getvalue())
        self.assertIn('pending=true', stderr.getvalue())
        self.assertIn('detail=Se agotaron los reintentos', stderr.getvalue())

    def test_mysql_disconnect_errno_finds_driver_errno_in_the_exception_cause(self):
        driver_error = RuntimeError(2013, 'lost connection')
        wrapped_error = OperationalError('database operation failed')
        wrapped_error.__cause__ = driver_error

        self.assertEqual(fixed_booking_repair._mysql_disconnect_errno(wrapped_error), 2013)

    def test_non_retryable_errors_do_not_recycle_the_connection(self):
        cases = (
            OperationalError(1205, 'lock wait timeout'),
            OperationalError(9999, 'other database error'),
            IntegrityError('duplicate'),
            ValidationError({'session': ['capacity reached']}),
        )
        for exc in cases:
            with self.subTest(exc=exc):
                mysql_connection = MagicMock(vendor='mysql')
                with patch.object(fixed_booking_repair, 'connection', mysql_connection), \
                      patch.object(Booking.objects, 'create_fixed_booking_while_locked', side_effect=exc):
                    if isinstance(exc, ValidationError):
                        results = fixed_booking_repair.repair_expected_fixed_bookings(
                            start_date=self.session.date, end_date=self.session.date, apply=True,
                        )
                        self.assertEqual(results[0]['accion'], 'SKIP_CAPACITY')
                    else:
                        with self.assertRaises(type(exc)):
                            fixed_booking_repair.repair_expected_fixed_bookings(
                                start_date=self.session.date, end_date=self.session.date, apply=True,
                            )
                mysql_connection.close.assert_not_called()
                mysql_connection.ensure_connection.assert_not_called()
