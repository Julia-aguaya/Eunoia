from datetime import date, time

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse

from scheduling.fixed_booking_capacity import assess_fixed_capacities, assess_fixed_capacity
from scheduling.models import Booking, BookingSource, BookingStatus, ClassSession, MonthlyAccessStatus, MonthlyAccessStatusType, Section, StudentMonthlyPlan, User, WeeklyClassSlot

from ._shared import TestCase, normalize_month_start


class FixedBookingCapacityTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='reformer_arriba')
        self.session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 19), start_time=time(20), end_time=time(21),
            capacity=7,
        )
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section, weekday=self.session.date.isoweekday(), start_time=self.session.start_time,
            end_time=self.session.end_time, is_active=True,
        )
        self.fixed_student = self.make_student('albertina@example.com', 'Albertina')
        StudentMonthlyPlan.objects.create(
            student=self.fixed_student, month=normalize_month_start(self.session.date), section=self.section,
        ).assign_weekly_slots([self.slot])

    def make_student(self, email, first_name):
        student = User.objects.create_user(
            email=email, password='secret123', first_name=first_name, last_name='Prueba', primary_section=self.section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=student, month=normalize_month_start(self.session.date),
            status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )
        return student

    def cancel_fixed_booking(self, student, **fields):
        booking = Booking.objects.create_booking(
            session=self.session,
            student=student,
            source=BookingSource.FIXED_SLOT,
        )
        Booking.objects.filter(pk=booking.pk).update(
            status=BookingStatus.CANCELLED,
            cancelled_at=timezone.now(),
            **fields,
        )
        return booking

    def test_booked_fixed_booking_occupies_one_spot(self):
        Booking.objects.create_booking(session=self.session, student=self.fixed_student)

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.active_booking_count, 1)
        self.assertEqual(assessment.pending_fixed_student_ids, ())
        self.assertEqual(assessment.committed_count, 1)

    def test_missing_fixed_booking_reserves_one_spot(self):
        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.pending_fixed_student_ids, (self.fixed_student.pk,))
        self.assertEqual(assessment.committed_count, 1)

    def test_student_cancelled_fixed_booking_does_not_reserve_a_spot(self):
        self.cancel_fixed_booking(
            self.fixed_student,
            cancelled_by_id=self.fixed_student.pk,
            cancellation_generates_recovery=True,
        )

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.active_booking_count, 0)
        self.assertEqual(assessment.pending_fixed_student_ids, ())

    def test_student_cancelled_fixed_booking_leaves_physical_spot_for_recovery(self):
        self.session.capacity = 1
        self.session.save(update_fields=['capacity', 'updated_at'])
        self.cancel_fixed_booking(
            self.fixed_student,
            cancelled_by_id=self.fixed_student.pk,
            cancellation_generates_recovery=True,
        )

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.available_recovery_spots, 1)

    def test_non_restorable_history_does_not_reserve_a_spot(self):
        self.cancel_fixed_booking(
            self.fixed_student,
            cancellation_generates_recovery=True,
        )

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.pending_fixed_student_ids, ())

    def test_global_deactivation_history_does_not_reserve_a_spot(self):
        self.cancel_fixed_booking(
            self.fixed_student,
            cancellation_reason='global_deactivation',
        )

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.pending_fixed_student_ids, ())

    def test_moved_fixed_booking_history_does_not_reserve_a_spot(self):
        moved_session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 20), start_time=time(20), end_time=time(21), capacity=7,
        )
        self.cancel_fixed_booking(self.fixed_student, moved_to_session=moved_session)

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.pending_fixed_student_ids, ())

    def test_recovery_used_fixed_booking_history_does_not_reserve_a_spot(self):
        credit = self.fixed_student.recovery_credits.create(
            section=self.section,
            source='manual',
            status='used',
            expires_at=date(2026, 11, 19),
            used_at=timezone.now(),
        )
        self.cancel_fixed_booking(self.fixed_student, used_recovery_credit=credit)

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.pending_fixed_student_ids, ())

    def test_restorable_fixed_booking_reserves_a_spot(self):
        self.cancel_fixed_booking(self.fixed_student, cancellation_generates_recovery=False)

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.pending_fixed_student_ids, (self.fixed_student.pk,))

    def test_booked_fixed_and_recovery_bookings_each_occupy_one_spot(self):
        fixed_student = self.make_student('fixed-booked@example.com', 'FixedBooked')
        Booking.objects.create_booking(session=self.session, student=self.fixed_student)
        Booking.objects.create_booking(
            session=self.session,
            student=fixed_student,
            source=BookingSource.MAKEUP,
        )

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.active_booking_count, 2)
        self.assertEqual(assessment.committed_count, 2)

    def test_real_full_session_blocks_recovery_without_projected_missing_booking(self):
        self.session.capacity = 1
        self.session.save(update_fields=['capacity', 'updated_at'])
        recovery_student = self.make_student('real-full@example.com', 'RealFull')
        self.cancel_fixed_booking(
            self.fixed_student,
            cancelled_by_id=self.fixed_student.pk,
            cancellation_generates_recovery=True,
        )
        Booking.objects.create(session=self.session, student=recovery_student, source=BookingSource.MAKEUP)

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.available_recovery_spots, 0)
        self.assertFalse(assessment.has_fixed_capacity_conflict)

    def test_bulk_assessment_applies_the_same_history_policy(self):
        self.cancel_fixed_booking(
            self.fixed_student,
            cancelled_by_id=self.fixed_student.pk,
            cancellation_generates_recovery=True,
        )

        assessment = assess_fixed_capacities(sessions=[self.session])[self.session.pk]

        self.assertEqual(assessment.pending_fixed_student_ids, ())

    def test_albertina_equivalent_full_session_reserves_zero_recovery_spots(self):
        for index in range(7):
            student = self.make_student(f'active-{index}@example.com', f'Active{index}')
            Booking.objects.create_booking(
                session=self.session,
                student=student,
                source=BookingSource.MAKEUP if index == 0 else BookingSource.FIXED_SLOT,
            )

        assessment = assess_fixed_capacity(session=self.session)

        self.assertEqual(assessment.active_booking_count, 7)
        self.assertEqual(assessment.pending_fixed_student_ids, (self.fixed_student.pk,))
        self.assertEqual(assessment.available_recovery_spots, 0)
        self.assertTrue(assessment.has_fixed_capacity_conflict)
        self.assertEqual(Booking.objects.filter(session=self.session, status=BookingStatus.BOOKED).count(), 7)

    def test_recovery_creation_rejects_capacity_committed_to_missing_fixed_booking(self):
        recovery_student = self.make_student('recovery@example.com', 'Recovery')
        for index in range(6):
            Booking.objects.create_booking(
                session=self.session,
                student=self.make_student(f'filled-{index}@example.com', f'Filled{index}'),
            )

        with self.assertRaises(ValidationError):
            Booking.objects.create_booking(
                session=self.session,
                student=recovery_student,
                source=BookingSource.MAKEUP,
            )

        self.assertEqual(Booking.objects.filter(session=self.session, status=BookingStatus.BOOKED).count(), 6)

    def test_recovery_availability_get_does_not_write(self):
        from django.test import Client

        credit = self.fixed_student.recovery_credits.create(
            section=self.section,
            source='manual',
            status='available',
            expires_at=date(2026, 11, 19),
        )
        before = {
            'sessions': ClassSession.objects.count(),
            'bookings': Booking.objects.count(),
            'plans': StudentMonthlyPlan.objects.count(),
        }
        client = Client()
        client.force_login(self.fixed_student)

        response = client.get(reverse('use-recovery', args=[credit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(before['sessions'], ClassSession.objects.count())
        self.assertEqual(before['bookings'], Booking.objects.count())
        self.assertEqual(before['plans'], StudentMonthlyPlan.objects.count())
