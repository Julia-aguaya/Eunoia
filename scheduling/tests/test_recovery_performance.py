from datetime import datetime
from time import perf_counter
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext

from scheduling.fixed_booking_capacity import assess_fixed_capacity

from ._shared import *


class RecoveryAvailabilityPerformanceTests(TestCase):
    """Regression coverage for bulk recovery availability across all activities."""

    def setUp(self):
        self.now = timezone.make_aware(datetime(2026, 8, 13, 12, 0))
        self.today = self.now.date()
        self.sections = [
            Section.objects.get(code='cadillac'),
            Section.objects.get(code='reformer_arriba'),
            Section.objects.get(code='reformer_abajo'),
        ]
        self.student = User.objects.create_user(
            email='profile-student@example.com', password='secret123', first_name='Profile', last_name='Student',
            primary_section=self.sections[0], must_change_password=False,
        )
        self.client.force_login(self.student)
        for section in self.sections:
            slot = WeeklyClassSlot.objects.create(
                section=section, weekday=Weekday.THURSDAY, start_time=time(9), end_time=time(10), is_active=True,
            )
            StudentMonthlyPlan.objects.create(
                student=self.student, month=date(2026, 8, 1), section=section,
            ).assign_weekly_slots([slot])

        for offset in range(42):
            day = self.today + timedelta(days=offset)
            if day.day == 1:
                MonthlyAccessStatus.objects.get_or_create(
                    student=self.student, month=day,
                    defaults={'status': MonthlyAccessStatusType.ACTIVE, 'booking_enabled': True},
                )
            for section in self.sections:
                for hour in (9, 10, 11):
                    ClassSession.objects.create(
                        section=section, date=day, start_time=time(hour), end_time=time(hour + 1),
                        capacity=12, status=SessionStatus.SCHEDULED,
                    )
        MonthlyAccessStatus.objects.get_or_create(
            student=self.student, month=date(2026, 8, 1),
            defaults={'status': MonthlyAccessStatusType.ACTIVE, 'booking_enabled': True},
        )
        self.credits = [
            RecoveryCredit.objects.create(
                student=self.student, section=self.sections[index % len(self.sections)],
                source=RecoveryCreditSource.MANUAL, status=RecoveryCreditStatus.AVAILABLE,
                expires_at=self.today + timedelta(days=30 + index),
            )
            for index in range(8)
        ]
        self.focus_credit = self.credits[0]

        fixed_student = User.objects.create_user(
            email='pending-fixed@example.com', password='secret123', first_name='Fixed', last_name='Student',
            primary_section=self.sections[0], must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=fixed_student, month=date(2026, 8, 1),
            status=MonthlyAccessStatusType.ACTIVE, booking_enabled=True,
        )
        slot = WeeklyClassSlot.objects.get(
            section=self.sections[2], weekday=Weekday.THURSDAY, start_time=time(9), end_time=time(10),
        )
        StudentMonthlyPlan.objects.create(
            student=fixed_student, month=date(2026, 8, 1), section=self.sections[2],
        ).assign_weekly_slots([slot])

    def get_recovery(self, section):
        with patch('scheduling.views.timezone.localdate', return_value=self.today), patch(
            'scheduling.views.timezone.now', return_value=self.now
        ):
            return self.client.get(
                reverse('use-recovery', args=[self.focus_credit.pk]), {'section': section.code},
            )

    def test_bulk_get_is_bounded_across_sections_credits_and_42_day_horizon(self):
        before = {
            'sessions': ClassSession.objects.count(),
            'bookings': Booking.objects.count(),
            'plans': StudentMonthlyPlan.objects.count(),
            'credits': RecoveryCredit.objects.count(),
        }
        measurements = {}
        for section in self.sections:
            started = perf_counter()
            with CaptureQueriesContext(connection) as captured:
                response = self.get_recovery(section)
            measurements[section.code] = (len(captured), perf_counter() - started, response)
            self.assertEqual(response.status_code, 200)
            self.assertGreater(response.context['eligible_sessions_count'], 0)

        # This ceiling guards the common GET. It must not grow with sessions ×
        # credits × whole-day audit executions.
        self.assertLessEqual(max(item[0] for item in measurements.values()), 40)
        self.assertLess(max(item[1] for item in measurements.values()), 2.0)
        self.assertEqual(before['sessions'], ClassSession.objects.count())
        self.assertEqual(before['bookings'], Booking.objects.count())
        self.assertEqual(before['plans'], StudentMonthlyPlan.objects.count())
        self.assertEqual(before['credits'], RecoveryCredit.objects.count())

        candidates = list(ClassSession.objects.filter(
            section=self.sections[2], date__range=(date(2026, 8, 8), date(2026, 8, 14)),
        ))
        with CaptureQueriesContext(connection) as legacy_queries:
            for session in candidates:
                for credit in self.credits:
                    if credit.is_session_compatible(session):
                        assess_fixed_capacity(session=session)
        self.assertGreater(len(legacy_queries), 0, f'legacy_queries={len(legacy_queries)}')
        self.assertGreater(len(legacy_queries), max(item[0] for item in measurements.values()) * 2)

    def test_profiles_with_history_and_nonavailable_credits_return_controlled_response(self):
        target = ClassSession.objects.filter(section=self.sections[0], date__gt=self.today).first()
        Booking.objects.create(session=target, student=self.student, status=BookingStatus.CANCELLED)
        RecoveryCredit.objects.create(
            student=self.student, section=self.sections[0], source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.USED, expires_at=self.today + timedelta(days=10), used_at=self.now,
        )
        RecoveryCredit.objects.create(
            student=self.student, section=self.sections[1], source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE, expires_at=self.today - timedelta(days=1),
        )
        response = self.get_recovery(self.sections[1])

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.context['eligible_sessions_count'], 0)
