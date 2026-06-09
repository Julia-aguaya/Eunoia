from datetime import datetime
from unittest.mock import patch

from ._shared import *


class WebRecoveryFlowTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.fixed_now = timezone.make_aware(datetime(2026, 6, 10, 12, 0))
        self.today = self.fixed_now.date()
        self.student = User.objects.create_user(
            email='web-recovery@example.com',
            password='WebRecovery2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
            must_change_password=False,
        )
        self.student.temporary_password_set_at = None
        self.student.save(update_fields=['temporary_password_set_at', 'updated_at'])
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.today,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        self.client.force_login(self.student)

    def create_session(self, *, section=None, days=3, status=SessionStatus.SCHEDULED, start_hour=9, capacity=4):
        return ClassSession.objects.create(
            section=section or self.section,
            date=self.today + timedelta(days=days),
            start_time=time(start_hour, 0),
            end_time=time(start_hour + 1, 0),
            capacity=capacity,
            status=status,
        )

    def create_session_on(self, target_date, *, section=None, status=SessionStatus.SCHEDULED, start_hour=9, capacity=4):
        return ClassSession.objects.create(
            section=section or self.section,
            date=target_date,
            start_time=time(start_hour, 0),
            end_time=time(start_hour + 1, 0),
            capacity=capacity,
            status=status,
        )

    def create_available_credit(self, *, origin_session=None, expires_at=None, status=RecoveryCreditStatus.AVAILABLE):
        return RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.TIMELY_CANCELLATION,
            status=status,
            origin_session=origin_session,
            expires_at=expires_at or (self.today + timedelta(days=30)),
        )

    def post_recovery_booking(self, session, credit, *, next_url=None):
        return self.client.post(
            reverse('create-booking', args=[session.pk]),
            {
                'used_recovery_credit_id': credit.pk,
                'next': next_url or reverse('my-bookings'),
            },
            follow=True,
        )

    def test_recovery_page_shows_only_available_same_section_slots_in_current_workweek(self):
        monday = self.today - timedelta(days=self.today.weekday())
        tuesday = monday + timedelta(days=1)
        thursday = monday + timedelta(days=3)
        friday = monday + timedelta(days=4)

        origin_session = self.create_session_on(tuesday, start_hour=8)
        eligible_session = self.create_session_on(thursday, start_hour=10)
        self.create_session_on(self.today, start_hour=10)
        full_session = self.create_session_on(friday, start_hour=11, capacity=1)
        other_student = User.objects.create_user(
            email='occupied-recovery@example.com',
            password='OccupiedRecovery2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=other_student,
            month=self.today,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        Booking.objects.create(session=full_session, student=other_student)
        next_week_session = self.create_session_on(monday + timedelta(days=7), start_hour=9)
        self.create_session_on(thursday, section=self.other_section, start_hour=12)
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clases disponibles de esta semana laboral')
        self.assertContains(response, '10:00 a 11:00')
        self.assertContains(response, 'Usar recuperacion')
        self.assertNotContains(response, self.other_section.name)
        self.assertNotContains(response, 'No compatible')
        self.assertNotContains(response, '11:00 a 12:00')
        self.assertEqual(response.context['eligible_sessions_count'], 1)
        self.assertEqual(
            [card['session'].pk for card in response.context['recovery_session_cards']],
            [eligible_session.pk],
        )
        self.assertNotIn(next_week_session.pk, [card['session'].pk for card in response.context['recovery_session_cards']])

    def test_recovery_page_empty_state_mentions_current_workweek(self):
        monday = self.today - timedelta(days=self.today.weekday())
        tuesday = monday + timedelta(days=1)
        origin_session = self.create_session_on(tuesday, start_hour=8)
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay horarios disponibles para recuperar en la semana laboral actual de esta actividad.')

    def test_student_can_book_from_recovery_flow(self):
        origin_session = self.create_session(days=2, start_hour=8)
        target_session = self.create_session(days=6, start_hour=12)
        credit = self.create_available_credit(origin_session=origin_session)
        MonthlyAccessStatus.objects.filter(student=self.student).delete()
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=target_session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )

        response = self.post_recovery_booking(target_session, credit)

        booking = Booking.objects.get(session=target_session, student=self.student)
        credit.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(booking.source, 'makeup')
        self.assertEqual(booking.used_recovery_credit, credit)
        self.assertEqual(credit.status, RecoveryCreditStatus.USED)
        self.assertContains(response, 'usando tu recuperacion disponible')
        self.assertContains(response, 'Recuperacion aplicada')

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, '1 aplicadas')

    def test_expired_recovery_shows_clear_error(self):
        target_session = self.create_session(days=5)
        credit = self.create_available_credit(expires_at=self.today - timedelta(days=1))
        if normalize_month_start(target_session.date) != normalize_month_start(self.today):
            MonthlyAccessStatus.objects.create(
                student=self.student,
                month=target_session.date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )

        with patch('scheduling.models.timezone.localdate', return_value=self.today), patch(
            'scheduling.models.timezone.now', return_value=self.fixed_now
        ):
            response = self.post_recovery_booking(target_session, credit, next_url=reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(session=target_session, student=self.student).exists())
        self.assertContains(response, 'La recuperacion elegida esta vencida y ya no puede usarse.')

    def test_missing_recovery_in_post_shows_clear_error(self):
        target_session = self.create_session(days=5)

        response = self.client.post(
            reverse('create-booking', args=[target_session.pk]),
            {'used_recovery_credit_id': 999999, 'next': reverse('agenda')},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La recuperacion elegida ya no esta disponible en tu portal.')

    def test_use_recovery_page_redirects_when_credit_is_not_available(self):
        used_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.TIMELY_CANCELLATION,
            status=RecoveryCreditStatus.USED,
            expires_at=self.today + timedelta(days=30),
            used_at=timezone.now(),
        )

        response = self.client.get(reverse('use-recovery', args=[used_credit.pk]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('my-bookings'))
        self.assertContains(response, 'La recuperacion elegida ya no esta disponible para usar.')
