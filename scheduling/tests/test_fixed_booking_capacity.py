from datetime import date, time

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse

from scheduling.fixed_booking_capacity import assess_fixed_capacity
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
