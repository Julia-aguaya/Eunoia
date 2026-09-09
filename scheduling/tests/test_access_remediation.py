from datetime import date, time
from io import StringIO

from ._shared import *


class AutomaticAccessImpactRemediationTests(TestCase):
    def setUp(self):
        self.section, _ = Section.objects.get_or_create(code='cadillac', defaults={'name': 'Cadillac'})
        self.student = User.objects.create_user(
            email='impacted@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section, is_active=False,
        )
        self.reviewer = User.objects.create_superuser(email='reviewer@example.com', password='secret123')
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section, weekday=Weekday.FRIDAY, start_time=time(9), end_time=time(10),
        )
        self.plan = StudentMonthlyPlan.objects.create(
            student=self.student, month=date(2026, 8, 1), section=self.section, is_active=False,
        )
        self.plan.assign_weekly_slots([self.slot])
        self.access = MonthlyAccessStatus.objects.create(
            student=self.student, month=date(2026, 8, 1),
            status=MonthlyAccessStatusType.PENDING_PAYMENT, booking_enabled=False,
        )
        self.session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 7), start_time=time(9), end_time=time(10), capacity=4,
        )

    def cancelled_booking(self, *, origin=None, cancelled_by=None):
        return Booking.objects.create(
            session=self.session, student=self.student, status=BookingStatus.CANCELLED,
            source=BookingSource.FIXED_SLOT, cancelled_at=timezone.now(),
            cancelled_by=cancelled_by, cancellation_origin=origin,
        )

    def run_command(self, *args):
        out, err = StringIO(), StringIO()
        call_command(
            'remediate_automatic_access_impact', '--start-date', '2026-08-01', '--end-date', '2026-08-31',
            *args, stdout=out, stderr=err,
        )
        return out.getvalue(), err.getvalue()

    def test_automatic_cancellation_restores_access_booking_and_missing_future_fixed_booking_idempotently(self):
        booking = self.cancelled_booking(origin=BookingCancellationOrigin.AUTOMATIC_ACCESS_IMPACT)
        future_session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 14), start_time=time(9), end_time=time(10), capacity=4,
        )

        self.run_command('--apply')
        self.run_command('--apply')

        self.student.refresh_from_db()
        self.access.refresh_from_db()
        self.plan.refresh_from_db()
        booking.refresh_from_db()
        self.assertTrue(self.student.is_active)
        self.assertTrue(self.access.booking_enabled)
        self.assertTrue(self.plan.is_active)
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertIsNone(booking.cancellation_origin)
        self.assertEqual(Booking.objects.filter(session=future_session, student=self.student, status=BookingStatus.BOOKED).count(), 1)

    def test_student_staff_manual_and_unknown_cancellations_are_not_restored(self):
        for origin, actor in (
            (BookingCancellationOrigin.STUDENT_SELF_SERVICE, self.student),
            (BookingCancellationOrigin.STAFF_MANUAL, self.reviewer),
            (None, None),
        ):
            with self.subTest(origin=origin):
                booking = self.cancelled_booking(origin=origin, cancelled_by=actor)
                self.run_command('--apply')
                booking.refresh_from_db()
                self.assertEqual(booking.status, BookingStatus.CANCELLED)
                booking.delete()

    def test_explicitly_approved_legacy_cancellation_is_restored(self):
        booking = self.cancelled_booking()
        BookingRemediationApproval.objects.create(
            booking=booking, approved_by=self.reviewer, notes='Reviewed against the legacy export.',
        )

        out, _ = self.run_command('--apply')

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertIn('RESTORED_APPROVED_LEGACY', out)

    def test_capacity_safeguard_keeps_booking_and_access_artifacts_unchanged(self):
        self.session.capacity = 1
        self.session.save(update_fields=['capacity', 'updated_at'])
        other = User.objects.create_user(
            email='other@example.com', password='secret123', first_name='Grace', last_name='Hopper',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(student=other, month=date(2026, 8, 1), booking_enabled=True)
        Booking.objects.create(session=self.session, student=other, source=BookingSource.MANUAL)
        booking = self.cancelled_booking(origin=BookingCancellationOrigin.AUTOMATIC_ACCESS_IMPACT)

        out, _ = self.run_command('--apply')

        booking.refresh_from_db()
        self.student.refresh_from_db()
        self.access.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertFalse(self.student.is_active)
        self.assertFalse(self.access.booking_enabled)
        self.assertFalse(self.plan.is_active)
        self.assertIn('SKIP_RESTORE_SAFEGUARD', out)

    def test_manual_suspension_blocks_an_automatic_candidate(self):
        booking = self.cancelled_booking(origin=BookingCancellationOrigin.AUTOMATIC_ACCESS_IMPACT)
        self.student.manual_suspension = True
        self.student.save(update_fields=['manual_suspension', 'updated_at'])

        out, _ = self.run_command('--apply')

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertIn('RESPECT_MANUAL_SUSPENSION', out)
