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
        with patch('scheduling.models.timezone.localdate', return_value=self.today), patch(
            'scheduling.models.timezone.now', return_value=self.fixed_now
        ), patch('scheduling.views.timezone.localdate', return_value=self.today), patch(
            'scheduling.views.timezone.now', return_value=self.fixed_now
        ):
            return self.client.post(
                reverse('create-booking', args=[session.pk]),
                {
                    'used_recovery_credit_id': credit.pk,
                    'next': next_url or reverse('my-bookings'),
                },
                follow=True,
            )

    def test_recovery_page_shows_only_available_same_section_slots_in_visible_month(self):
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
        self.assertNotContains(
            response,
            'Naranja = hay cupo. Línea punteada = la clase está publicada, pero hoy no tiene lugar. Podés tocar cualquier fecha marcada para revisar los horarios del día.',
        )
        self.assertContains(response, 'Lunes')
        self.assertContains(response, 'Miércoles')
        self.assertContains(response, 'Día con horarios para recuperar')
        self.assertContains(response, '10:00')
        self.assertContains(response, 'Confirmar recuperación')
        self.assertNotContains(response, self.other_section.name)
        self.assertNotContains(response, '11:00 a 12:00')
        self.assertEqual(response.context['eligible_sessions_count'], 1)
        self.assertEqual(
            [card['session'].pk for card in response.context['recovery_session_cards']],
            [eligible_session.pk],
        )
        self.assertNotIn(next_week_session.pk, [card['session'].pk for card in response.context['recovery_session_cards']])

    def test_recovery_page_allows_selecting_relevant_day_without_available_slots(self):
        monday_now = timezone.make_aware(datetime(2026, 6, 8, 9, 0))
        monday = monday_now.date()
        wednesday = monday + timedelta(days=2)
        origin_session = self.create_session_on(monday, start_hour=8)
        available_session = self.create_session_on(monday, start_hour=18)
        credit = self.create_available_credit(origin_session=origin_session)
        WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            starts_on=monday,
            is_active=True,
        )
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.other_section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            starts_on=monday,
            is_active=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(monday),
            section=self.other_section,
        )
        plan.assign_weekly_slots([planned_slot])

        with patch('scheduling.views.timezone.now', return_value=monday_now), patch(
            'scheduling.views.timezone.localdate', return_value=monday
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]), {'date': wednesday.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '18:00 - no disponible')
        self.assertContains(response, f'Miércoles {wednesday.strftime("%d/%m")}')
        self.assertNotContains(response, 'Confirmar recuperación')
        self.assertEqual(response.context['recovery_selected_date'], wednesday)
        self.assertEqual(len(response.context['recovery_selected_day_cards']), 1)
        self.assertEqual(
            [card['session'].pk for card in response.context['recovery_session_cards']],
            [available_session.pk],
        )
        calendar_days = [
            day
            for week in response.context['recovery_calendar_weeks']
            for day in week
            if day['date'] in {monday, wednesday}
        ]
        self.assertEqual(len(calendar_days), 2)
        self.assertTrue(all(day['select_url'] for day in calendar_days))
        self.assertTrue(any(day['date'] == wednesday and not day['has_availability'] for day in calendar_days))

    def test_recovery_page_marks_only_current_selected_day(self):
        monday = self.today - timedelta(days=self.today.weekday())
        thursday = monday + timedelta(days=3)
        friday = monday + timedelta(days=4)
        origin_session = self.create_session_on(thursday, start_hour=8)
        first_available_session = self.create_session_on(thursday, start_hour=18)
        second_available_session = self.create_session_on(friday, start_hour=19)
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            response = self.client.get(
                reverse('use-recovery', args=[credit.pk]),
                {'date': friday.isoformat(), 'session': second_available_session.pk},
            )

        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(html.count('is-selectable selected'), 1)
        self.assertIn('has-available-recovery is-selectable', html)
        self.assertEqual(response.context['recovery_selected_date'], friday)
        self.assertEqual(response.context['recovery_selected_session_card']['session'].pk, second_available_session.pk)
        self.assertNotEqual(first_available_session.date, response.context['recovery_selected_date'])

    def test_recovery_page_shows_full_slots_as_blocked_labels(self):
        monday = self.today - timedelta(days=self.today.weekday())
        tuesday = monday + timedelta(days=1)
        friday = monday + timedelta(days=4)
        origin_session = self.create_session_on(tuesday, start_hour=8)
        full_session = self.create_session_on(friday, start_hour=11, capacity=1)
        other_student = User.objects.create_user(
            email='full-recovery-slot@example.com',
            password='FullRecovery2026!',
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
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]), {'date': friday.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '11:00 - cupo completo')
        self.assertContains(response, 'Clase publicada sin cupo')
        self.assertContains(response, 'slot-button blocked full')
        self.assertNotContains(response, 'Confirmar recuperación')
        self.assertIsNone(response.context['recovery_selected_session_card'])
        calendar_days = {
            day['date']: day
            for week in response.context['recovery_calendar_weeks']
            for day in week
            if day['date'] == friday
        }
        self.assertTrue(calendar_days[friday]['has_published_recovery'])
        self.assertTrue(calendar_days[friday]['has_unavailable_recovery'])
        self.assertTrue(calendar_days[friday]['is_selectable'])

    def test_recovery_page_marks_habitual_plan_days_like_agenda(self):
        monday = self.today - timedelta(days=self.today.weekday())
        wednesday = monday + timedelta(days=2)
        origin_session = self.create_session_on(monday, start_hour=8)
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.other_section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.other_section,
        )
        plan.assign_weekly_slots([planned_slot])
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]))

        self.assertEqual(response.status_code, 200)
        calendar_days = {
            day['date']: day
            for week in response.context['recovery_calendar_weeks']
            for day in week
            if day['date'] == wednesday
        }
        self.assertTrue(calendar_days[wednesday]['has_habitual_plan'])

    def test_recovery_page_empty_state_mentions_current_week(self):
        monday = self.today - timedelta(days=self.today.weekday())
        tuesday = monday + timedelta(days=1)
        origin_session = self.create_session_on(tuesday, start_hour=8)
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '08:00 - no disponible')
        self.assertEqual(response.context['recovery_selected_date'], tuesday)
        self.assertEqual(len(response.context['recovery_selected_day_cards']), 1)

    def test_recovery_page_uses_saturday_as_week_boundary(self):
        sunday_now = timezone.make_aware(datetime(2026, 6, 14, 12, 0))
        sunday = sunday_now.date()
        current_cycle_tuesday = date(2026, 6, 16)
        origin_session = self.create_session_on(date(2026, 6, 9), start_hour=8)
        eligible_session = self.create_session_on(current_cycle_tuesday, start_hour=10)
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=sunday_now), patch(
            'scheduling.views.timezone.localdate', return_value=sunday
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Elegí un día y un horario de esta semana para usar tu recuperación.')
        self.assertContains(response, eligible_session.start_time.strftime('%H:%M'))
        self.assertFalse(response.context['recovery_workweek_is_next'])
        self.assertEqual(response.context['eligible_sessions_count'], 1)
        self.assertEqual(response.context['recovery_week_start'], date(2026, 6, 13))
        self.assertEqual(response.context['recovery_week_end'], date(2026, 6, 19))
        self.assertEqual(
            [card['session'].pk for card in response.context['recovery_session_cards']],
            [eligible_session.pk],
        )

    def test_recovery_page_keeps_current_week_visible_on_friday_night(self):
        friday_now = timezone.make_aware(datetime(2026, 6, 12, 21, 30))
        friday = friday_now.date()
        previous_saturday = date(2026, 6, 6)
        thursday = date(2026, 6, 11)
        origin_session = self.create_session_on(previous_saturday, start_hour=8)
        past_available_session = self.create_session_on(thursday, start_hour=10)
        full_session = self.create_session_on(thursday, start_hour=11, capacity=1)
        other_student = User.objects.create_user(
            email='friday-boundary@example.com',
            password='FridayBoundary2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=other_student,
            month=friday,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        Booking.objects.create(session=full_session, student=other_student)
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=friday_now), patch(
            'scheduling.views.timezone.localdate', return_value=friday
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]), {'date': thursday.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['recovery_week_start'], previous_saturday)
        self.assertEqual(response.context['recovery_week_end'], friday)
        self.assertEqual(response.context['recovery_selected_date'], thursday)
        self.assertContains(response, '10:00 - ya pasó')
        self.assertContains(response, '11:00 - cupo completo')
        self.assertNotContains(response, 'Confirmar recuperación')
        self.assertIsNone(response.context['recovery_selected_session_card'])
        self.assertEqual(len(response.context['recovery_selected_day_cards']), 2)

        calendar_days = {
            day['date']: day
            for week in response.context['recovery_calendar_weeks']
            for day in week
            if day['date'] == thursday
        }
        self.assertTrue(calendar_days[thursday]['is_selectable'])
        self.assertTrue(calendar_days[thursday]['has_unavailable_recovery'])

    def test_recovery_page_keeps_blocked_days_selectable_until_friday_night(self):
        friday_now = timezone.make_aware(datetime(2026, 6, 12, 21, 0))
        friday = friday_now.date()
        monday = friday - timedelta(days=friday.weekday())
        tuesday = monday + timedelta(days=1)
        origin_session = self.create_session_on(monday, start_hour=8)
        full_session = self.create_session_on(tuesday, start_hour=11, capacity=1)
        other_student = User.objects.create_user(
            email='friday-night-recovery@example.com',
            password='FridayNightRecovery2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=other_student,
            month=friday,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        Booking.objects.create(session=full_session, student=other_student)
        credit = self.create_available_credit(origin_session=origin_session)

        with patch('scheduling.views.timezone.now', return_value=friday_now), patch(
            'scheduling.views.timezone.localdate', return_value=friday
        ):
            response = self.client.get(reverse('use-recovery', args=[credit.pk]), {'date': tuesday.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['recovery_workweek_is_next'])
        self.assertEqual(response.context['recovery_selected_date'], tuesday)
        self.assertContains(response, '11:00 - cupo completo')
        self.assertNotContains(response, 'Confirmar recuperación')
        self.assertEqual(len(response.context['recovery_selected_day_cards']), 1)
        calendar_days = {
            day['date']: day
            for week in response.context['recovery_calendar_weeks']
            for day in week
            if day['date'] == tuesday
        }
        self.assertTrue(calendar_days[tuesday]['has_published_recovery'])
        self.assertTrue(calendar_days[tuesday]['has_unavailable_recovery'])
        self.assertTrue(calendar_days[tuesday]['is_selectable'])
        self.assertTrue(calendar_days[tuesday]['select_url'])

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
        self.assertContains(response, 'Usada')

        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, '1 aplicadas')

    def test_student_can_use_recovery_during_cross_month_grace_window_without_new_access(self):
        fixed_now = timezone.make_aware(datetime(2026, 6, 27, 12, 0))
        today = fixed_now.date()
        self.fixed_now = fixed_now
        self.today = today
        MonthlyAccessStatus.objects.filter(student=self.student).delete()
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=today,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        origin_session = self.create_session_on(today, start_hour=8)
        target_session = self.create_session_on(date(2026, 7, 1), start_hour=12)
        credit = self.create_available_credit(origin_session=origin_session, expires_at=today + timedelta(days=30))
        MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 7, 1)).delete()

        response = self.post_recovery_booking(target_session, credit)

        booking = Booking.objects.get(session=target_session, student=self.student)
        credit.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(booking.source, 'makeup')
        self.assertEqual(booking.used_recovery_credit, credit)
        self.assertEqual(credit.status, RecoveryCreditStatus.USED)
        self.assertContains(response, 'usando tu recuperacion disponible')

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
