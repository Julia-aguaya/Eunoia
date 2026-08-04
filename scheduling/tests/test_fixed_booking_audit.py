from datetime import date, time

from ._shared import *
from scheduling.fixed_booking_audit import audit_expected_fixed_bookings, classify_bookings


class FixedBookingAuditTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.student = User.objects.create_user(
            email='audit-student@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section,
        )
        self.session = ClassSession.objects.create(
            section=self.section, date=date(2026, 8, 5), start_time=time(9), end_time=time(10),
            capacity=10, status=SessionStatus.SCHEDULED,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student, month=date(2026, 8, 1), status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )

    def booking(self, status=BookingStatus.BOOKED, **fields):
        booking = Booking.objects.create_booking(session=self.session, student=self.student)
        Booking.objects.filter(pk=booking.pk).update(status=status, **fields)
        booking.refresh_from_db()
        return booking

    def test_classifies_a_to_e_deterministically(self):
        booked = self.booking()
        self.assertEqual(classify_bookings([booked])[1], 'A_booked')
        Booking.objects.filter(pk=booked.pk).delete()

        cancelled = self.booking(
            BookingStatus.CANCELLED, cancelled_by_id=self.student.id, cancellation_generates_recovery=True,
        )
        self.assertEqual(classify_bookings([cancelled])[1], 'B_cancelled_student_with_recovery')
        Booking.objects.filter(pk=cancelled.pk).delete()

        other = self.booking(BookingStatus.ATTENDED)
        self.assertEqual(classify_bookings([other])[1], 'C_other_status_attended')
        self.assertEqual(classify_bookings([])[1], 'D_never_booked')
        duplicate = Booking(id=100, session=self.session, student=self.student, status=BookingStatus.BOOKED)
        second_active = Booking(id=101, session=self.session, student=self.student, status=BookingStatus.BOOKED)
        self.assertEqual(classify_bookings([other, duplicate, second_active])[1], 'E_multiple_active_bookings')

    def test_classifies_staff_and_technical_cancellations(self):
        staff = User.objects.create_user(
            email='audit-staff@example.com', password='secret123', first_name='Grace', last_name='Hopper', is_staff=True,
        )
        staff_cancelled = self.booking(BookingStatus.CANCELLED, cancelled_by_id=staff.id)
        self.assertEqual(classify_bookings([staff_cancelled])[1], 'B_cancelled_staff_without_recovery')
        Booking.objects.filter(pk=staff_cancelled.pk).delete()

        technical_cancelled = self.booking(BookingStatus.CANCELLED)
        self.assertEqual(classify_bookings([technical_cancelled])[1], 'B_cancelled_technical_or_other_without_recovery')

    def test_audits_only_explicitly_eligible_fixed_plan_pairs(self):
        slot = WeeklyClassSlot.objects.create(
            section=self.section, weekday=self.session.date.isoweekday(), start_time=self.session.start_time,
            end_time=self.session.end_time, is_active=True,
        )
        self.session.slot = slot
        self.session.save(update_fields=['slot', 'updated_at'])
        plan = StudentMonthlyPlan.objects.create(student=self.student, month=date(2026, 8, 1), section=self.section)
        plan.assign_weekly_slots([slot])
        rows = list(audit_expected_fixed_bookings(start_date=self.session.date, end_date=self.session.date))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['plan_id'], plan.id)
        self.assertEqual(rows[0]['clasificacion'], 'D_never_booked')
