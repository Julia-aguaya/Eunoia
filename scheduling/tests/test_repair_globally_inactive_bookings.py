import csv
from datetime import date, time
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from scheduling.management.commands.repair_globally_inactive_bookings import Command

from ._shared import (
    Booking,
    BookingCancellationReason,
    BookingSource,
    BookingStatus,
    ClassSession,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    RecoveryCreditSource,
    RecoveryCreditStatus,
    Section,
    SessionStatus,
    StudentMonthlyPlan,
    StudentMonthlyPlanSlot,
    TestCase,
    User,
    WeeklyClassSlot,
    normalize_month_start,
)


class RepairGloballyInactiveBookingsCommandTests(TestCase):
    from_date = date(2026, 8, 5)

    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.inactive_student = self.create_student('inactive@example.com', active=True)
        self.active_student = self.create_student('active@example.com', active=True)
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=self.from_date.isoweekday(),
            start_time=time(11),
            end_time=time(12),
        )
        self.grant_booking_eligibility(self.inactive_student)
        self.grant_booking_eligibility(self.active_student)
        self.included = self.create_booking(self.inactive_student, self.from_date, time(8))
        self.same_day_past_class = self.create_booking(self.inactive_student, self.from_date, time(6))
        self.earlier = self.create_booking(self.inactive_student, date(2026, 8, 4), time(9))
        self.active = self.create_booking(self.active_student, self.from_date, time(9))
        self.cancelled = self.create_booking(self.inactive_student, self.from_date, time(10))
        Booking.objects.filter(pk=self.cancelled.pk).update(status=BookingStatus.CANCELLED)
        self.credit = RecoveryCredit.objects.create(
            student=self.inactive_student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=date(2026, 11, 5),
        )
        # Simulate legacy active bookings left behind by a global deactivation.
        User.objects.filter(pk=self.inactive_student.pk).update(is_active=False)

    def create_student(self, email, *, active):
        return User.objects.create_user(
            email=email,
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            is_active=active,
        )

    def create_booking(self, student, session_date, start_time):
        session = ClassSession.objects.create(
            section=self.section,
            date=session_date,
            start_time=start_time,
            end_time=time(start_time.hour + 1),
            capacity=4,
            status=SessionStatus.SCHEDULED,
        )
        booking = Booking(
            student=student,
            session=session,
            status=BookingStatus.BOOKED,
            source=BookingSource.MANUAL,
        )
        booking.save()
        return booking

    def grant_booking_eligibility(self, student):
        plan = StudentMonthlyPlan.objects.create(
            student=student,
            month=normalize_month_start(self.from_date),
            section=self.section,
        )
        plan.assign_weekly_slots([self.slot])
        MonthlyAccessStatus.objects.create(
            student=student,
            month=normalize_month_start(self.from_date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        return plan

    def run_command(self, *args):
        stdout = StringIO()
        stderr = StringIO()
        call_command(
            'repair_globally_inactive_bookings',
            '--from-date', '2026-08-05',
            *args,
            stdout=stdout,
            stderr=stderr,
        )
        return stdout.getvalue(), stderr.getvalue()

    def test_dry_run_reports_exact_candidates_without_writes_or_locks(self):
        locks = Mock()
        with patch(
            'scheduling.management.commands.repair_globally_inactive_bookings.transaction.atomic'
        ) as atomic, patch.object(
            User.objects, 'select_for_update', wraps=User.objects.select_for_update
        ) as user_lock, patch.object(
            ClassSession.objects, 'select_for_update', wraps=ClassSession.objects.select_for_update
        ) as session_lock, patch.object(
            Booking.objects, 'select_for_update', wraps=Booking.objects.select_for_update
        ) as booking_lock, patch.object(
            StudentMonthlyPlan.objects, 'select_for_update', wraps=StudentMonthlyPlan.objects.select_for_update
        ) as plan_lock, patch.object(
            StudentMonthlyPlanSlot.objects, 'select_for_update', wraps=StudentMonthlyPlanSlot.objects.select_for_update
        ) as plan_slot_lock:
            locks.attach_mock(user_lock, 'user')
            locks.attach_mock(session_lock, 'session')
            locks.attach_mock(booking_lock, 'booking')
            locks.attach_mock(plan_lock, 'plan')
            locks.attach_mock(plan_slot_lock, 'plan_slot')
            with CaptureQueriesContext(connection) as queries:
                stdout, stderr = self.run_command()

        self.assertEqual(
            stdout.splitlines()[0],
            'record_type,student_id,student_name,session_id,date,time,section,current_status,plan_id,plan_month,plan_section,plan_slot_ids,plan_slot_details,action',
        )
        rows = list(csv.DictReader(StringIO(stdout)))
        self.assertEqual(len(rows), 3)
        self.assertEqual({row['action'] for row in rows}, {'WOULD_CANCEL', 'WOULD_DELETE_PLAN'})
        self.assertEqual(
            {row['session_id'] for row in rows if row['record_type'] == 'BOOKING'},
            {str(self.included.session_id), str(self.same_day_past_class.session_id)},
        )
        atomic.assert_not_called()
        self.assertEqual(locks.mock_calls, [])
        self.assertFalse(
            [
                query['sql']
                for query in queries
                if query['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
            ]
        )
        self.assertEqual(Booking.objects.get(pk=self.included.pk).status, BookingStatus.BOOKED)
        self.assertEqual(Booking.objects.get(pk=self.same_day_past_class.pk).status, BookingStatus.BOOKED)
        self.assertEqual(MonthlyAccessStatus.objects.count(), 2)
        self.assertEqual(StudentMonthlyPlan.objects.count(), 2)
        self.assertEqual(StudentMonthlyPlanSlot.objects.count(), 2)
        self.assertEqual(RecoveryCredit.objects.count(), 1)
        self.assertNotIn('mode=', stdout)
        self.assertEqual(
            stderr,
            'repair_globally_inactive_bookings mode=dry-run booking_candidates=2 plan_candidates=1 applied=0 skipped=0\n',
        )

    def test_apply_cancels_canonical_candidates_and_is_idempotent(self):
        locks = Mock()
        with patch.object(
            User.objects, 'select_for_update', wraps=User.objects.select_for_update
        ) as user_lock, patch.object(
            ClassSession.objects, 'select_for_update', wraps=ClassSession.objects.select_for_update
        ) as session_lock, patch.object(
            Booking.objects, 'select_for_update', wraps=Booking.objects.select_for_update
        ) as booking_lock:
            locks.attach_mock(user_lock, 'user')
            locks.attach_mock(session_lock, 'session')
            locks.attach_mock(booking_lock, 'booking')
            first_stdout, first_stderr = self.run_command('--apply')
        second_stdout, second_stderr = self.run_command('--apply')

        for booking in (self.included, self.same_day_past_class):
            booking.refresh_from_db()
            self.assertEqual(booking.status, BookingStatus.CANCELLED)
            self.assertEqual(booking.cancellation_reason, BookingCancellationReason.GLOBAL_DEACTIVATION)
            self.assertFalse(booking.cancellation_generates_recovery)
            self.assertIsNotNone(booking.cancelled_at)
        self.assertEqual(Booking.objects.get(pk=self.earlier.pk).status, BookingStatus.BOOKED)
        self.assertEqual(Booking.objects.get(pk=self.active.pk).status, BookingStatus.BOOKED)
        self.assertEqual(Booking.objects.get(pk=self.cancelled.pk).status, BookingStatus.CANCELLED)
        self.assertEqual(MonthlyAccessStatus.objects.count(), 2)
        self.assertEqual(StudentMonthlyPlan.objects.filter(student=self.inactive_student).count(), 0)
        self.assertEqual(StudentMonthlyPlanSlot.objects.filter(monthly_plan__student=self.inactive_student).count(), 0)
        self.assertEqual(RecoveryCredit.objects.count(), 1)
        self.assertEqual(first_stdout.count('CANCELLED'), 2)
        self.assertEqual(first_stdout.count('DELETED_PLAN'), 1)
        self.assertNotIn('mode=', first_stdout)
        self.assertEqual(
            first_stderr,
            'repair_globally_inactive_bookings mode=apply booking_candidates=2 plan_candidates=1 applied=3 skipped=0\n',
        )
        self.assertEqual(
            [call[0] for call in locks.mock_calls],
            ['user', 'session', 'booking', 'user', 'session', 'booking', 'user'],
        )
        self.assertEqual(second_stdout.splitlines(), [
            'record_type,student_id,student_name,session_id,date,time,section,current_status,plan_id,plan_month,plan_section,plan_slot_ids,plan_slot_details,action',
        ])
        self.assertNotIn('mode=', second_stdout)
        self.assertEqual(
            second_stderr,
            'repair_globally_inactive_bookings mode=apply booking_candidates=0 plan_candidates=0 applied=0 skipped=0\n',
        )

    def test_apply_skips_candidate_that_fails_locked_revalidation(self):
        original_row = Command._row

        def invalidate_included_booking(booking, *, action):
            row = original_row(booking, action=action)
            if action == 'WOULD_CANCEL' and booking.pk == self.included.pk:
                Booking.objects.filter(pk=booking.pk).update(status=BookingStatus.CANCELLED)
            return row

        with patch.object(Command, '_row', side_effect=invalidate_included_booking):
            stdout, stderr = self.run_command('--apply')

        rows = {row['session_id']: row for row in csv.DictReader(StringIO(stdout))}
        self.assertEqual(rows[str(self.included.session_id)]['action'], 'SKIPPED_REVALIDATION')
        self.assertEqual(rows[str(self.included.session_id)]['current_status'], BookingStatus.CANCELLED)
        self.assertEqual(rows[str(self.same_day_past_class.session_id)]['action'], 'CANCELLED')
        self.assertEqual(Booking.objects.get(pk=self.included.pk).status, BookingStatus.CANCELLED)
        self.assertEqual(Booking.objects.get(pk=self.same_day_past_class.pk).status, BookingStatus.CANCELLED)
        self.assertNotIn('mode=', stdout)
        self.assertEqual(
            stderr,
            'repair_globally_inactive_bookings mode=apply booking_candidates=2 plan_candidates=1 applied=2 skipped=1\n',
        )

    def test_apply_skips_booking_deleted_after_candidate_selection(self):
        original_row = Command._row

        def delete_included_booking(booking, *, action):
            row = original_row(booking, action=action)
            if action == 'WOULD_CANCEL' and booking.pk == self.included.pk:
                Booking.objects.filter(pk=booking.pk).delete()
            return row

        with patch.object(Command, '_row', side_effect=delete_included_booking):
            stdout, stderr = self.run_command('--apply')

        rows = {row['session_id']: row for row in csv.DictReader(StringIO(stdout))}
        self.assertEqual(rows[str(self.included.session_id)]['action'], 'SKIPPED_DELETED_BOOKING')
        self.assertEqual(rows[str(self.included.session_id)]['current_status'], '')
        self.assertEqual(rows[str(self.same_day_past_class.session_id)]['action'], 'CANCELLED')
        self.assertFalse(Booking.objects.filter(pk=self.included.pk).exists())
        self.assertEqual(
            stderr,
            'repair_globally_inactive_bookings mode=apply booking_candidates=2 plan_candidates=1 applied=2 skipped=1\n',
        )

    def test_apply_skips_plan_deleted_after_candidate_selection(self):
        original_plan_row = Command._plan_row
        target_plan = StudentMonthlyPlan.objects.get(
            student=self.inactive_student,
            month=normalize_month_start(self.from_date),
        )

        def delete_target_plan(plan, *, action):
            row = original_plan_row(plan, action=action)
            if action == 'WOULD_DELETE_PLAN' and plan.pk == target_plan.pk:
                StudentMonthlyPlan.objects.filter(pk=plan.pk).delete()
            return row

        with patch.object(Command, '_plan_row', side_effect=delete_target_plan):
            stdout, stderr = self.run_command('--apply')

        rows = list(csv.DictReader(StringIO(stdout)))
        plan_row = next(row for row in rows if row['plan_id'] == str(target_plan.pk))
        self.assertEqual(plan_row['action'], 'SKIPPED_DELETED_PLAN')
        self.assertFalse(StudentMonthlyPlan.objects.filter(pk=target_plan.pk).exists())
        self.assertEqual(
            stderr,
            'repair_globally_inactive_bookings mode=apply booking_candidates=2 plan_candidates=1 applied=2 skipped=1\n',
        )

    def test_apply_deletes_inactive_current_and_future_plans_and_preserves_access_and_history(self):
        prior_plan = StudentMonthlyPlan.objects.create(
            student=self.inactive_student,
            month=date(2026, 7, 1),
            section=self.section,
        )
        prior_plan.assign_weekly_slots([self.slot])
        future_plan = StudentMonthlyPlan.objects.create(
            student=self.inactive_student,
            month=date(2026, 9, 1),
            section=self.section,
        )
        future_plan.assign_weekly_slots([self.slot])
        target_plan = StudentMonthlyPlan.objects.get(
            student=self.inactive_student,
            month=normalize_month_start(self.from_date),
        )
        target_slot = target_plan.plan_slots.get()
        active_plan = StudentMonthlyPlan.objects.get(
            student=self.active_student,
            month=normalize_month_start(self.from_date),
        )
        access_ids = set(MonthlyAccessStatus.objects.values_list('pk', flat=True))

        stdout, _ = self.run_command('--apply')
        rows = list(csv.DictReader(StringIO(stdout)))
        plan_row = next(row for row in rows if row['plan_id'] == str(target_plan.pk))

        self.assertEqual(plan_row['action'], 'DELETED_PLAN')
        self.assertEqual(plan_row['plan_month'], '2026-08-01')
        self.assertEqual(plan_row['plan_section'], self.section.name)
        self.assertEqual(plan_row['plan_slot_ids'], str(target_slot.pk))
        self.assertIn(f'{target_slot.pk}:weekly_slot={self.slot.pk}', plan_row['plan_slot_details'])
        self.assertFalse(StudentMonthlyPlan.objects.filter(pk=target_plan.pk).exists())
        self.assertFalse(StudentMonthlyPlanSlot.objects.filter(pk=target_slot.pk).exists())
        self.assertTrue(StudentMonthlyPlan.objects.filter(pk=prior_plan.pk).exists())
        self.assertFalse(StudentMonthlyPlan.objects.filter(pk=future_plan.pk).exists())
        self.assertTrue(StudentMonthlyPlan.objects.filter(pk=active_plan.pk).exists())
        self.assertEqual(set(MonthlyAccessStatus.objects.values_list('pk', flat=True)), access_ids)

    def test_no_candidate_inactive_student_gets_reset_barrier_only_on_apply(self):
        no_candidate_student = self.create_student('no-candidates@example.com', active=False)

        self.run_command()

        no_candidate_student.refresh_from_db()
        self.assertIsNone(no_candidate_student.monthly_plan_reset_from)

        self.run_command('--apply')

        no_candidate_student.refresh_from_db()
        self.assertEqual(no_candidate_student.monthly_plan_reset_from, date(2026, 8, 1))

    def test_apply_retains_an_earlier_existing_reset_barrier(self):
        User.objects.filter(pk=self.inactive_student.pk).update(
            monthly_plan_reset_from=date(2026, 7, 1),
        )

        self.run_command('--apply')

        self.inactive_student.refresh_from_db()
        self.assertEqual(self.inactive_student.monthly_plan_reset_from, date(2026, 7, 1))

    def test_from_date_is_required_and_strict(self):
        with self.assertRaises(CommandError):
            call_command('repair_globally_inactive_bookings')
        with self.assertRaises(CommandError):
            call_command('repair_globally_inactive_bookings', '--from-date', '2026-8-5')
        with self.assertRaises(CommandError):
            call_command('repair_globally_inactive_bookings', '--from-date', '2026-08-5')
        with self.assertRaises(CommandError):
            call_command('repair_globally_inactive_bookings', '--from-date', '2026-08-05T00:00:00')
