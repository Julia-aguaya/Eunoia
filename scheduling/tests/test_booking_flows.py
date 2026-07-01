from datetime import datetime
from unittest.mock import patch

from ._shared import *

class StudentPortalViewTests(TestCase):
    def setUp(self):
        self.fixed_now = timezone.make_aware(datetime(2026, 6, 8, 12, 0))
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.student = User.objects.create_user(
            email='portal-student@example.com',
            password='PortalPass2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
            must_change_password=False,
        )
        self.student.temporary_password_set_at = None
        self.student.save(update_fields=['temporary_password_set_at', 'updated_at'])
        self.today = self.fixed_now.date()
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.today,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        self.session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=3),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        self.second_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=5),
            start_time=time(15, 0),
            end_time=time(16, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        if normalize_month_start(self.second_session.date) != normalize_month_start(self.today):
            MonthlyAccessStatus.objects.create(
                student=self.student,
                month=self.second_session.date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )
        self.other_session = ClassSession.objects.create(
            section=self.other_section,
            date=self.today + timedelta(days=4),
            start_time=time(11, 0),
            end_time=time(12, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=self.session, student=self.student)
        RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today + timedelta(days=20),
        )
        self.client.force_login(self.student)

    def get_portal_page(self, url, *, fixed_now=None, today=None):
        fixed_now = fixed_now or self.fixed_now
        today = today or self.today
        with patch('scheduling.views.timezone.now', return_value=fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=today
        ):
            return self.client.get(url)

    def test_dashboard_displays_operational_summary(self):
        response = self.get_portal_page(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Próxima clase')
        self.assertContains(response, 'Esta semana')
        self.assertContains(response, '1 disponible')
        self.assertContains(response, 'Portal habilitado')
        self.assertContains(response, self.section.name)
        self.assertNotContains(response, '<strong>Inicio</strong>', html=False)
        self.assertNotContains(response, '<strong>Mis turnos</strong>', html=False)
        self.assertNotContains(response, 'Reservar clase')
        self.assertNotContains(response, 'Ver agenda')

    def test_agenda_only_shows_primary_section_sessions(self):
        response = self.get_portal_page(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.section.name)
        self.assertContains(response, 'Tus clases confirmadas')
        self.assertNotContains(response, self.other_section.name)

    def test_agenda_shows_secondary_section_when_monthly_plan_exists_for_it(self):
        other_slot = WeeklyClassSlot.objects.create(
            section=self.other_section,
            weekday=self.other_session.date.isoweekday(),
            start_time=self.other_session.start_time,
            end_time=self.other_session.end_time,
            is_active=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.other_section,
        )
        plan.assign_weekly_slots([other_slot])
        self.other_session.slot = other_slot
        self.other_session.save(update_fields=['slot', 'updated_at'])

        response = self.get_portal_page(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.other_section.name)
        self.assertFalse(Booking.objects.filter(session=self.other_session, student=self.student, status=BookingStatus.BOOKED).exists())

    def test_my_bookings_shows_active_booking_and_recovery_credit(self):
        response = self.get_portal_page(reverse('my-bookings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recuperaciones')
        self.assertContains(response, 'Ver horarios')
        self.assertContains(response, 'Cómo usarla')

    def test_my_bookings_history_shows_legacy_used_recovery_context(self):
        legacy_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.USED,
            expires_at=self.today + timedelta(days=90),
            used_at=timezone.make_aware(datetime(2026, 6, 13, 19, 0)),
            notes=(
                '[legacy-recoverableturns-import]\n'
                'source=eunoia.recoverableturns.json\n'
                'legacy_recoverableturn_id=legacy-turn-used\n'
                'legacy_user_id=legacy-student-1\n'
                'legacy_original_day=Viernes\n'
                'legacy_original_hour=19:00\n'
                'legacy_cancelled_week=2026-06-06T15:00:00+00:00\n'
                'legacy_recovered=true\n'
                'legacy_recovery_date=2026-06-13T19:00:00+00:00\n'
                'legacy_assigned_day=Martes\n'
                'legacy_assigned_hour=20:00\n'
                '[/legacy-recoverableturns-import]'
            ),
        )

        response = self.get_portal_page(reverse('my-bookings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recuperación legacy ya usada')
        self.assertContains(response, 'Usada el 13/06/2026')
        self.assertContains(response, 'Original: Viernes 19:00 hs')
        self.assertContains(response, 'Asignada a: Martes 20:00 hs')
        self.assertContains(response, 'Legacy')

        detail_response = self.get_portal_page(f"{reverse('my-bookings')}?credit_detail={legacy_credit.id}")

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Fecha usada')
        self.assertContains(detail_response, 'Turno original')
        self.assertContains(detail_response, 'Turno asignado')
        self.assertContains(detail_response, 'Viernes 19:00 hs')
        self.assertContains(detail_response, 'Martes 20:00 hs')

    def test_account_page_shows_basic_profile_and_rules(self):
        response = self.client.get(reverse('account'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.get_full_name())
        self.assertContains(response, self.student.email)
        self.assertContains(response, 'Mi actividad')
        self.assertContains(response, 'Información importante')

    def test_portal_uses_effective_monthly_plan_section_when_primary_section_is_missing(self):
        reformer_abajo = Section.objects.get(code='reformer_abajo')
        Booking.objects.filter(student=self.student).delete()
        self.student.primary_section = None
        self.student.save(update_fields=['primary_section', 'updated_at'])

        friday_slot = WeeklyClassSlot.objects.create(
            section=reformer_abajo,
            weekday=Weekday.FRIDAY,
            start_time=time(19, 0),
            end_time=time(20, 0),
            is_active=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=reformer_abajo,
        )
        plan.assign_weekly_slots([friday_slot])
        generated_session = ClassSession.objects.create(
            slot=friday_slot,
            section=reformer_abajo,
            date=date(2026, 6, 12),
            start_time=time(19, 0),
            end_time=time(20, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )

        self.get_portal_page(reverse('agenda'))
        dashboard_response = self.get_portal_page(reverse('dashboard'))
        account_response = self.get_portal_page(reverse('account'))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(dashboard_response.context['primary_section'].code, 'reformer_abajo')
        self.assertGreaterEqual(dashboard_response.context['upcoming_turns_count'], 1)
        self.assertTrue(dashboard_response.context['operational_status']['can_operate'])
        self.assertContains(dashboard_response, 'Reformer Abajo')
        self.assertContains(dashboard_response, '19:00')
        self.assertContains(dashboard_response, 'Cancelar turno')
        self.assertEqual(generated_session.status, SessionStatus.SCHEDULED)

        self.assertEqual(account_response.status_code, 200)
        self.assertContains(account_response, 'Reformer Abajo')

    def test_dashboard_does_not_generate_missing_plan_sessions_on_get(self):
        Booking.objects.filter(student=self.student).delete()
        future_date = date(2026, 6, 10)
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=future_date.isoweekday(),
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        )
        plan.assign_weekly_slots([planned_slot])

        response = self.get_portal_page(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ClassSession.objects.filter(
                section=self.section,
                date=future_date,
                start_time=time(18, 0),
            ).exists()
        )
        self.assertContains(response, 'Plan mensual')
        self.assertContains(response, '18:00')

    def test_agenda_does_not_generate_or_reconcile_missing_plan_sessions_on_get(self):
        Booking.objects.filter(student=self.student).delete()
        future_date = date(2026, 6, 10)
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=future_date.isoweekday(),
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        ).assign_weekly_slots([planned_slot])

        response = self.get_portal_page(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ClassSession.objects.filter(
                section=self.section,
                date=future_date,
                start_time=time(18, 0),
            ).exists()
        )
        self.assertFalse(
            Booking.objects.filter(
                student=self.student,
                session__section=self.section,
                session__date=future_date,
                session__start_time=time(18, 0),
                status=BookingStatus.BOOKED,
            ).exists()
        )
        self.assertContains(response, '18:00')

    def test_account_page_updates_profile_data(self):
        response = self.client.post(
            reverse('account'),
            {
                'first_name': 'Adriana',
                'last_name': 'Lovelace',
                'email': 'adriana@example.com',
                'phone': '1133344455',
                'current_password': '',
                'new_password1': '',
                'new_password2': '',
            },
            follow=True,
        )

        self.student.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.student.first_name, 'Adriana')
        self.assertEqual(self.student.email, 'adriana@example.com')
        self.assertEqual(self.student.phone, '1133344455')
        self.assertContains(response, 'Actualizamos tus datos de la cuenta.')

    def test_account_page_changes_password_when_current_password_matches(self):
        response = self.client.post(
            reverse('account'),
            {
                'first_name': self.student.first_name,
                'last_name': self.student.last_name,
                'email': self.student.email,
                'phone': self.student.phone,
                'current_password': 'PortalPass2026!',
                'new_password1': 'NuevaSegura2026!',
                'new_password2': 'NuevaSegura2026!',
            },
            follow=True,
        )

        self.student.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.student.check_password('NuevaSegura2026!'))
        self.assertContains(response, 'Actualizamos tus datos de la cuenta.')

    def test_dashboard_shows_only_current_week_bookings(self):
        next_week_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=10),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        if normalize_month_start(next_week_session.date) != normalize_month_start(self.today):
            MonthlyAccessStatus.objects.get_or_create(
                student=self.student,
                month=normalize_month_start(next_week_session.date),
                defaults={
                    'status': MonthlyAccessStatusType.ACTIVE,
                    'booking_enabled': True,
                },
            )
        Booking.objects.create_booking(session=next_week_session, student=self.student)

        response = self.get_portal_page(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.session.start_time.strftime('%H:%M'))
        self.assertNotContains(response, next_week_session.start_time.strftime('%H:%M'))

    def test_dashboard_switches_to_next_workweek_on_saturday(self):
        saturday = date(2026, 6, 13)
        saturday_now = timezone.make_aware(datetime(2026, 6, 13, 12, 0))
        next_week_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 6, 15),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=next_week_session, student=self.student)

        response = self.get_portal_page(reverse('dashboard'), fixed_now=saturday_now, today=saturday)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Proxima semana')
        self.assertContains(response, '15/06 al 19/06')
        self.assertContains(response, next_week_session.start_time.strftime('%H:%M'))

    def test_dashboard_uses_monthly_plan_to_show_weekly_slots(self):
        Booking.objects.filter(student=self.student).delete()
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        planned_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 6, 10),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=planned_slot,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        )
        plan.assign_weekly_slots([planned_slot])

        response = self.get_portal_page(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Turnos de la semana')
        self.assertContains(response, planned_session.start_time.strftime('%H:%M'))
        self.assertContains(response, 'Clase confirmada')
        self.assertContains(response, 'Cancelar turno')

    def test_dashboard_shows_cancel_cta_when_monthly_plan_session_was_auto_booked(self):
        Booking.objects.filter(student=self.student).delete()
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        planned_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 6, 10),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=planned_slot,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        )
        plan.assign_weekly_slots([planned_slot])

        response = self.get_portal_page(reverse('dashboard'))

        auto_booking = Booking.objects.get(session=planned_session, student=self.student)
        weekly_plan_cards = response.context['weekly_plan_cards']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(auto_booking.source, BookingSource.FIXED_SLOT)
        self.assertTrue(any(card['booking'] and card['booking'].pk == auto_booking.pk for card in weekly_plan_cards))
        self.assertContains(response, 'Cancelar turno')

    def test_dashboard_labels_started_booking_as_clase_usada_instead_of_closed_window(self):
        past_session = ClassSession.objects.create(
            section=self.section,
            date=self.today,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        past_booking = Booking.objects.create_booking(session=past_session, student=self.student)

        response = self.get_portal_page(reverse('dashboard'))

        next_card = response.context['next_portal_turn_card']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(next_card['booking'].pk, past_booking.pk)
        self.assertEqual(next_card['cancel_action']['label'], 'Clase usada')
        self.assertContains(response, 'Clase usada')
        self.assertNotContains(response, 'Ventana cerrada')

    def test_dashboard_keeps_closed_window_label_for_upcoming_booking_inside_two_hours(self):
        Booking.objects.filter(student=self.student).delete()
        near_session = ClassSession.objects.create(
            section=self.section,
            date=self.today,
            start_time=time(13, 30),
            end_time=time(14, 30),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        near_booking = Booking.objects.create_booking(session=near_session, student=self.student)

        response = self.get_portal_page(reverse('dashboard'))

        next_card = response.context['next_portal_turn_card']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(next_card['booking'].pk, near_booking.pk)
        self.assertEqual(next_card['cancel_action']['label'], 'Ventana cerrada')
        self.assertContains(response, 'Ventana cerrada')
        self.assertNotContains(response, 'Clase usada')

    def test_dashboard_auto_booking_is_idempotent_for_fixed_plan_sessions(self):
        Booking.objects.filter(student=self.student).delete()
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        planned_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 6, 10),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=planned_slot,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        )
        plan.assign_weekly_slots([planned_slot])

        first_response = self.get_portal_page(reverse('dashboard'))
        second_response = self.get_portal_page(reverse('dashboard'))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Booking.objects.filter(session=planned_session, student=self.student).count(), 1)
        self.assertEqual(
            Booking.objects.filter(session=planned_session, student=self.student, status=BookingStatus.BOOKED).count(),
            1,
        )

    def test_dashboard_shows_weekly_plan_cards_for_multiple_monthly_activities(self):
        Booking.objects.filter(student=self.student).delete()
        reformer_slot = WeeklyClassSlot.objects.create(
            section=self.other_section,
            weekday=Weekday.THURSDAY,
            start_time=time(11, 0),
            end_time=time(12, 0),
            is_active=True,
        )
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        ).assign_weekly_slots([
            WeeklyClassSlot.objects.create(
                section=self.section,
                weekday=Weekday.WEDNESDAY,
                start_time=time(18, 0),
                end_time=time(19, 0),
                is_active=True,
            )
        ])
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.other_section,
        ).assign_weekly_slots([reformer_slot])
        reformer_session = ClassSession.objects.create(
            section=self.other_section,
            slot=reformer_slot,
            date=date(2026, 6, 11),
            start_time=time(11, 0),
            end_time=time(12, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )

        response = self.get_portal_page(reverse('dashboard'))

        weekly_plan_cards = response.context['weekly_plan_cards']
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(card['session'] and card['session'].pk == reformer_session.pk for card in weekly_plan_cards))
        self.assertContains(response, 'Reformer Arriba')

    def test_fixed_plan_cancellation_does_not_reopen_manual_reservation_flow(self):
        Booking.objects.filter(student=self.student).delete()
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        planned_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 6, 10),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=planned_slot,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        )
        plan.assign_weekly_slots([planned_slot])

        self.get_portal_page(reverse('dashboard'))
        booking = Booking.objects.get(session=planned_session, student=self.student, status=BookingStatus.BOOKED)
        with patch('scheduling.views.timezone.now', return_value=self.fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            cancellation_response = self.client.post(
                reverse('cancel-booking', args=[booking.pk]),
                {'next': reverse('dashboard')},
                follow=True,
            )
        dashboard_response = self.get_portal_page(reverse('dashboard'))

        self.assertEqual(cancellation_response.status_code, 200)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(Booking.objects.filter(session=planned_session, student=self.student).count(), 1)
        self.assertEqual(Booking.objects.filter(session=planned_session, student=self.student, status=BookingStatus.BOOKED).count(), 0)
        self.assertContains(dashboard_response, 'Turno cancelado')

    def test_dashboard_uses_next_month_plan_when_next_workweek_starts_in_new_month(self):
        Booking.objects.filter(student=self.student).delete()
        next_month_plan_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        next_month_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 7, 1),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=next_month_plan_slot,
        )
        next_month_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=date(2026, 7, 1),
            section=self.section,
        )
        next_month_plan.assign_weekly_slots([next_month_plan_slot])
        saturday = date(2026, 6, 27)
        saturday_now = timezone.make_aware(datetime(2026, 6, 27, 12, 0))
        MonthlyAccessStatus.objects.get_or_create(
            student=self.student,
            month=date(2026, 7, 1),
            defaults={
                'status': MonthlyAccessStatusType.ACTIVE,
                'booking_enabled': True,
            },
        )

        response = self.get_portal_page(reverse('dashboard'), fixed_now=saturday_now, today=saturday)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Proxima semana')
        self.assertContains(response, next_month_session.start_time.strftime('%H:%M'))
        self.assertContains(response, 'Clase confirmada')

    def test_dashboard_reuses_previous_month_plan_until_admin_saves_a_new_one(self):
        Booking.objects.filter(student=self.student).delete()
        carried_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        carried_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 7, 1),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=carried_slot,
        )
        june_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=date(2026, 6, 1),
            section=self.section,
            notes='Plan que continua vigente',
        )
        june_plan.assign_weekly_slots([carried_slot])
        saturday = date(2026, 6, 27)
        saturday_now = timezone.make_aware(datetime(2026, 6, 27, 12, 0))
        MonthlyAccessStatus.objects.get_or_create(
            student=self.student,
            month=date(2026, 7, 1),
            defaults={
                'status': MonthlyAccessStatusType.ACTIVE,
                'booking_enabled': True,
            },
        )

        response = self.get_portal_page(reverse('dashboard'), fixed_now=saturday_now, today=saturday)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Proxima semana')
        self.assertContains(response, carried_session.start_time.strftime('%H:%M'))
        self.assertContains(response, 'Clase confirmada')

    def test_agenda_blocks_actions_when_operational_access_is_not_available(self):
        access = self.student.get_monthly_access_for(self.today)
        access.mark_pending_payment()

        response = self.get_portal_page(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Impaga')
        self.assertContains(response, 'Sin reservas por ahora')
        self.assertContains(response, 'Tus clases confirmadas')

    def test_agenda_shows_operational_states_for_capacity_and_existing_booking(self):
        full_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=6),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=1,
            status=SessionStatus.SCHEDULED,
        )
        if normalize_month_start(full_session.date) != normalize_month_start(self.today):
            MonthlyAccessStatus.objects.get_or_create(
                student=self.student,
                month=normalize_month_start(full_session.date),
                defaults={
                    'status': MonthlyAccessStatusType.ACTIVE,
                    'booking_enabled': True,
                },
            )
        other_student = User.objects.create_user(
            email='agenda-full-state@example.com',
            password='AgendaState2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=other_student,
            month=normalize_month_start(full_session.date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        Booking.objects.create_booking(session=full_session, student=other_student)

        response = self.get_portal_page(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Agenda')
        self.assertContains(response, self.section.name)

    def test_agenda_marks_monthly_plan_days_and_makeup_bookings(self):
        Booking.objects.filter(student=self.student).delete()
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        planned_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 6, 10),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=planned_slot,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        )
        plan.assign_weekly_slots([planned_slot])
        recovery_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today + timedelta(days=30),
        )
        makeup_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=4),
            start_time=time(11, 0),
            end_time=time(12, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=makeup_session, student=self.student, used_recovery_credit=recovery_credit)

        response = self.get_portal_page(reverse('agenda'))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lunes')
        self.assertContains(response, 'Miércoles')
        self.assertContains(response, 'Clase confirmada')
        self.assertContains(response, 'Recuperación')
        self.assertNotContains(response, 'Todo listo para reservar')
        self.assertContains(response, planned_session.start_time.strftime('%H:%M'))
        self.assertIn('has-monthly-plan', html)
        self.assertIn('has-makeup-booking', html)
        self.assertNotIn('legend-swatch plan', html)
        self.assertIn('calendar-day-marker plan', html)
        self.assertIn('calendar-day-marker makeup', html)

    def test_agenda_calendar_surfaces_multiple_bookings_on_same_day(self):
        extra_session = ClassSession.objects.create(
            section=self.section,
            date=self.session.date,
            start_time=time(17, 0),
            end_time=time(18, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        extra_booking = Booking.objects.create_booking(session=extra_session, student=self.student)

        response = self.get_portal_page(reverse('agenda'))
        target_day = next(
            day
            for week in response.context['agenda_calendar_weeks']
            for day in week
            if day['date'] == self.session.date
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [card['booking'].session_id for card in response.context['agenda_visible_booking_cards']],
            [self.session.id, extra_booking.session_id],
        )
        self.assertEqual(target_day['booking_count'], 2)
        self.assertEqual(target_day['regular_booking_count'], 2)
        self.assertEqual(target_day['makeup_booking_count'], 0)
        self.assertContains(response, 'aria-label="2 clases confirmadas"', html=False)

    def test_portal_labels_habitual_recovery_booking_as_confirmed_class(self):
        Booking.objects.filter(student=self.student).delete()
        planned_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.THURSDAY,
            start_time=time(14, 0),
            end_time=time(15, 0),
            is_active=True,
        )
        planned_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=3),
            start_time=time(14, 0),
            end_time=time(15, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=planned_slot,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=self.section,
        )
        plan.assign_weekly_slots([planned_slot])
        recovery_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today + timedelta(days=30),
        )
        booking = Booking.objects.create_booking(session=planned_session, student=self.student, used_recovery_credit=recovery_credit)

        dashboard_response = self.get_portal_page(reverse('dashboard'))
        agenda_response = self.get_portal_page(reverse('agenda'))

        next_card = dashboard_response.context['next_portal_turn_card']
        agenda_card = next(
            card for card in agenda_response.context['agenda_visible_booking_cards'] if card['booking'].pk == booking.pk
        )
        planned_day = next(
            day
            for week in agenda_response.context['agenda_calendar_weeks']
            for day in week
            if day['date'] == planned_session.date
        )
        self.assertEqual(next_card['status_label'], 'Clase confirmada')
        self.assertEqual(next_card['status_tone'], 'default')
        self.assertEqual(agenda_card['status_label'], 'Clase confirmada')
        self.assertEqual(agenda_card['status_tone'], 'default')
        self.assertTrue(planned_day['has_regular_booking'])
        self.assertFalse(planned_day['has_makeup_booking'])
        self.assertContains(dashboard_response, 'Clase confirmada')
        self.assertContains(agenda_response, 'Clase confirmada')

    def test_agenda_keeps_same_week_bookings_visible_across_month_boundary(self):
        Booking.objects.filter(student=self.student).delete()
        monday_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        wednesday_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        june_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=date(2026, 6, 1),
            section=self.section,
        )
        june_plan.assign_weekly_slots([monday_slot, wednesday_slot])
        july_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=date(2026, 7, 1),
            section=self.section,
        )
        july_plan.assign_weekly_slots([monday_slot, wednesday_slot])
        monday_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 6, 29),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=monday_slot,
        )
        wednesday_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 7, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
            slot=wednesday_slot,
        )
        saturday = date(2026, 6, 27)
        saturday_now = timezone.make_aware(datetime(2026, 6, 27, 12, 0))

        response = self.get_portal_page(
            f"{reverse('agenda')}?month=2026-06",
            fixed_now=saturday_now,
            today=saturday,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lunes 29 de junio')
        self.assertContains(response, 'Miércoles 1 de julio')
        self.assertContains(response, '2 clases visibles')
        self.assertContains(response, 'Cancelar turno', count=2)
        self.assertNotContains(response, 'Próximo horario fijo')
        self.assertEqual(
            [card['booking'].session_id for card in response.context['agenda_visible_booking_cards']],
            [monday_session.id, wednesday_session.id],
        )

    def test_dashboard_highlights_blocked_operational_state(self):
        access = self.student.get_monthly_access_for(self.today)
        access.suspend_operational_access()

        response = self.get_portal_page(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suspendida')
        self.assertContains(response, 'Sin reservas por ahora')
        self.assertContains(response, 'Agenda')

    def test_my_bookings_explains_operational_blocking(self):
        access = self.student.get_monthly_access_for(self.today)
        access.mark_pending_payment()

        response = self.get_portal_page(reverse('my-bookings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este mes no podés reservar ni cancelar desde el portal')
        self.assertContains(response, 'Tus turnos activos siguen visibles para seguimiento')

class WebBookingFlowTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.today = timezone.localdate()
        self.student = User.objects.create_user(
            email='web-booking@example.com',
            password='WebBooking2026!',
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

    def ensure_operational_access_for(self, target_date):
        target_month = normalize_month_start(target_date)
        if target_month == normalize_month_start(self.today):
            return
        MonthlyAccessStatus.objects.get_or_create(
            student=self.student,
            month=target_month,
            defaults={
                'status': MonthlyAccessStatusType.ACTIVE,
                'booking_enabled': True,
            },
        )

    def create_session(self, *, section=None, days=3, status=SessionStatus.SCHEDULED, capacity=3, start_hour=9):
        session = ClassSession.objects.create(
            section=section or self.section,
            date=self.today + timedelta(days=days),
            start_time=time(start_hour, 0),
            end_time=time(start_hour + 1, 0),
            capacity=capacity,
            status=status,
        )
        self.ensure_operational_access_for(session.date)
        return session

    def create_session_at(self, start_at, *, section=None, status=SessionStatus.SCHEDULED, capacity=3):
        local_start = timezone.localtime(start_at)
        session = ClassSession.objects.create(
            section=section or self.section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=(local_start + timedelta(hours=1)).time().replace(tzinfo=None),
            capacity=capacity,
            status=status,
        )
        self.ensure_operational_access_for(session.date)
        return session

    def post_booking(self, session):
        return self.client.post(
            reverse('create-booking', args=[session.pk]),
            {'next': reverse('agenda')},
            follow=True,
        )

    def post_cancellation(self, booking):
        return self.client.post(
            reverse('cancel-booking', args=[booking.pk]),
            {'next': reverse('my-bookings')},
            follow=True,
        )

    def test_student_can_book_future_session_from_agenda(self):
        session = self.create_session()

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Booking.objects.filter(session=session, student=self.student, status=BookingStatus.BOOKED).exists())
        self.assertContains(response, 'Reservaste Cadillac')
        self.assertContains(response, 'Tus clases confirmadas')
        my_bookings_response = self.client.get(reverse('my-bookings'))
        self.assertContains(my_bookings_response, 'Recuperaciones')
        self.assertContains(my_bookings_response, 'Cómo usarla')

    def test_student_can_book_session_from_effective_plan_section_when_primary_section_is_missing(self):
        reformer_abajo = Section.objects.get(code='reformer_abajo')
        self.student.primary_section = None
        self.student.save(update_fields=['primary_section', 'updated_at'])

        friday_slot = WeeklyClassSlot.objects.create(
            section=reformer_abajo,
            weekday=Weekday.FRIDAY,
            start_time=time(19, 0),
            end_time=time(20, 0),
            is_active=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.today),
            section=reformer_abajo,
        )
        plan.assign_weekly_slots([friday_slot])
        session = self.create_session(section=reformer_abajo, days=4, start_hour=19)

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Booking.objects.filter(session=session, student=self.student, status=BookingStatus.BOOKED).exists())
        self.assertContains(response, 'Reservaste Reformer Abajo')

    def test_student_can_book_cross_month_session_during_grace_window_without_new_month_access(self):
        fixed_now = timezone.make_aware(datetime(2026, 6, 27, 12, 0))
        today = fixed_now.date()
        self.today = today
        MonthlyAccessStatus.objects.filter(student=self.student).delete()
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=today,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        target_session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 7, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            capacity=3,
            status=SessionStatus.SCHEDULED,
        )
        MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 7, 1)).delete()

        with patch('scheduling.models.timezone.localdate', return_value=today), patch(
            'scheduling.models.timezone.now', return_value=fixed_now
        ), patch('scheduling.views.timezone.localdate', return_value=today), patch(
            'scheduling.views.timezone.now', return_value=fixed_now
        ):
            response = self.post_booking(target_session)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Booking.objects.filter(session=target_session, student=self.student, status=BookingStatus.BOOKED).exists())
        self.assertContains(response, 'Reservaste Cadillac')

    def test_migrated_student_can_book_generated_plan_session_without_primary_section(self):
        reformer_abajo = Section.objects.get(code='reformer_abajo')
        self.student.primary_section = None
        self.student.save(update_fields=['primary_section', 'updated_at'])

        target_date = self.today + timedelta(days=(7 - self.today.weekday()) if self.today.weekday() >= 5 else (4 - self.today.weekday()))
        start_hour = 19
        slot = WeeklyClassSlot.objects.create(
            section=reformer_abajo,
            weekday=target_date.isoweekday(),
            start_time=time(start_hour, 0),
            end_time=time(start_hour + 1, 0),
            is_active=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(target_date),
            section=reformer_abajo,
        )
        plan.assign_weekly_slots([slot])
        self.ensure_operational_access_for(target_date)

        fixed_now = timezone.make_aware(datetime.combine(self.today, time(9, 0)))
        with patch('scheduling.views.timezone.now', return_value=fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            self.client.get(reverse('agenda'), {'month': target_date.strftime('%Y-%m')})
        with patch('scheduling.views.timezone.now', return_value=fixed_now), patch(
            'scheduling.views.timezone.localdate', return_value=self.today
        ):
            dashboard_response = self.client.get(reverse('dashboard'))

        session = ClassSession.objects.get(
            section=reformer_abajo,
            date=target_date,
            start_time=time(start_hour, 0),
        )
        response = self.post_booking(session)

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Cancelar turno')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Booking.objects.filter(session=session, student=self.student, status=BookingStatus.BOOKED).exists())
        self.assertContains(response, 'Ya tenés una reserva activa para esta clase.')

    def test_student_without_operational_access_sees_clear_error(self):
        session = self.create_session()
        access = self.student.get_monthly_access_for(session.date)
        access.suspend_operational_access()

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(session=session, student=self.student).exists())
        self.assertContains(response, 'Este mes no podés reservar esta clase desde el portal.')

    def test_student_cannot_book_session_from_another_activity(self):
        session = self.create_session(section=self.other_section)

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(session=session, student=self.student).exists())
        self.assertContains(response, 'Esta clase corresponde a otra actividad. Solo podés reservar dentro de tus actividades asignadas.')

    def test_student_cannot_book_closed_session(self):
        session = self.create_session(status=SessionStatus.CANCELLED)

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(session=session, student=self.student).exists())
        self.assertContains(response, 'Esta clase ya esta cerrada y no acepta nuevas reservas.')

    def test_student_cannot_book_full_session(self):
        session = self.create_session(capacity=1)
        other_student = User.objects.create_user(
            email='capacity-other@example.com',
            password='Other2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=other_student,
            month=session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        Booking.objects.create_booking(session=session, student=other_student)

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(session=session, student=self.student).exists())
        self.assertContains(response, 'No quedan cupos disponibles para esta clase.')

    def test_student_cannot_duplicate_active_booking(self):
        session = self.create_session()
        Booking.objects.create_booking(session=session, student=self.student)

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.filter(session=session, student=self.student, status=BookingStatus.BOOKED).count(), 1)
        self.assertContains(response, 'Ya tenés una reserva activa para esta clase.')

    def test_student_can_cancel_future_booking_from_my_bookings(self):
        session = self.create_session(days=4)
        booking = Booking.objects.create_booking(session=session, student=self.student)

        response = self.post_cancellation(booking)

        booking.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertContains(response, 'Se genero una recuperacion disponible hasta el')
        self.assertContains(response, 'Usala antes de su vencimiento.')
        self.assertEqual(RecoveryCredit.objects.filter(student=self.student, status=RecoveryCreditStatus.AVAILABLE).count(), 1)

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, 'Todavía no tenés turnos esta semana.')
        self.assertContains(dashboard_response, '1 disponible')

    def test_dashboard_does_not_recreate_self_cancelled_fixed_slot_booking_from_monthly_plan(self):
        session = self.create_session(days=4)
        slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=session.date.isoweekday(),
            start_time=session.start_time,
            end_time=session.end_time,
            is_active=True,
        )
        session.slot = slot
        session.save(update_fields=['slot', 'updated_at'])
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(session.date),
            section=self.section,
            notes='Plan fijo portal',
        ).assign_weekly_slots([slot])
        booking = Booking.objects.create_booking(session=session, student=self.student)

        cancellation_response = self.post_cancellation(booking)
        dashboard_response = self.client.get(reverse('dashboard'))

        booking.refresh_from_db()
        self.assertEqual(cancellation_response.status_code, 200)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertEqual(Booking.objects.filter(session=session, student=self.student).count(), 1)
        self.assertFalse(
            Booking.objects.filter(
                session=session,
                student=self.student,
                status=BookingStatus.BOOKED,
            ).exists()
        )
        self.assertContains(dashboard_response, 'Turno cancelado')

    def test_student_cannot_cancel_booking_inside_two_hour_window(self):
        start_at = timezone.now() + timedelta(minutes=90)
        session = self.create_session_at(start_at)
        booking = Booking.objects.create_booking(session=session, student=self.student)

        response = self.post_cancellation(booking)

        booking.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertContains(response, 'Esta reserva ya no puede cancelarse desde la web porque faltan 2 horas o menos para la clase.')
        self.assertEqual(RecoveryCredit.objects.filter(student=self.student).count(), 0)

    def test_student_cannot_cancel_booking_that_is_already_inactive(self):
        session = self.create_session(days=4)
        booking = Booking.objects.create_booking(session=session, student=self.student)
        booking.cancel_by_student(actor=self.student, when=timezone.now())

        response = self.post_cancellation(booking)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Esta reserva ya no esta activa, asi que no se puede cancelar de nuevo desde la web.')
        self.assertEqual(RecoveryCredit.objects.filter(student=self.student).count(), 1)

    def test_student_cannot_cancel_someone_elses_booking(self):
        other_student = User.objects.create_user(
            email='other-cancel@example.com',
            password='OtherCancel2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
        )
        session = self.create_session(days=4)
        MonthlyAccessStatus.objects.create(
            student=other_student,
            month=normalize_month_start(session.date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        booking = Booking.objects.create_booking(session=session, student=other_student)

        response = self.client.post(reverse('cancel-booking', args=[booking.pk]))

        booking.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertFalse(RecoveryCredit.objects.filter(student=other_student, origin_session=session).exists())

class BookingReservationTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.student = User.objects.create_user(
            email='student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 4, 20),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        self.access = MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )

    def test_create_booking_uses_single_validated_pathway(self):
        booking = Booking.objects.create_booking(session=self.session, student=self.student)

        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertEqual(Booking.objects.count(), 1)

    def test_booking_requires_active_monthly_operational_access(self):
        self.access.suspend_operational_access()

        with self.assertRaisesMessage(ValidationError, 'active monthly operational access'):
            Booking.objects.create_booking(session=self.session, student=self.student)

    def test_booking_requires_same_primary_section(self):
        self.student.primary_section = self.other_section
        self.student.save()

        with self.assertRaisesMessage(ValidationError, 'assigned activities'):
            Booking.objects.create_booking(session=self.session, student=self.student)

    def test_booking_rejects_closed_sessions(self):
        self.session.status = SessionStatus.CANCELLED
        self.session.save()

        with self.assertRaisesMessage(ValidationError, 'cannot be booked'):
            Booking.objects.create_booking(session=self.session, student=self.student)

    def test_booking_rejects_when_capacity_is_full(self):
        other_student = User.objects.create_user(
            email='other@example.com',
            password='secret123',
            first_name='Katherine',
            last_name='Johnson',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=other_student,
            month=self.session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        third_student = User.objects.create_user(
            email='third@example.com',
            password='secret123',
            first_name='Dorothy',
            last_name='Vaughan',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=third_student,
            month=self.session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        Booking.objects.create_booking(session=self.session, student=self.student)
        Booking.objects.create_booking(session=self.session, student=other_student)

        with self.assertRaisesMessage(ValidationError, 'reached its capacity'):
            Booking.objects.create_booking(session=self.session, student=third_student)

    def test_booking_rejects_duplicate_active_booking_for_same_session(self):
        Booking.objects.create_booking(session=self.session, student=self.student)

        with self.assertRaisesMessage(ValidationError, 'already has an active booking'):
            Booking.objects.create_booking(session=self.session, student=self.student)

    def test_cancelled_booking_keeps_history_without_blocking_new_active_booking(self):
        cancelled_booking = Booking.objects.create(
            session=self.session,
            student=self.student,
            status=BookingStatus.CANCELLED,
        )

        new_booking = Booking.objects.create_booking(session=self.session, student=self.student)

        self.assertEqual(cancelled_booking.status, BookingStatus.CANCELLED)
        self.assertEqual(new_booking.status, BookingStatus.BOOKED)
        self.assertEqual(Booking.objects.filter(session=self.session, student=self.student).count(), 2)

    def test_fixed_plan_history_can_be_bypassed_for_reconciliation_rebooking(self):
        slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=self.session.date.isoweekday(),
            start_time=self.session.start_time,
            end_time=self.session.end_time,
            is_active=True,
        )
        self.session.slot = slot
        self.session.save(update_fields=['slot', 'updated_at'])
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=normalize_month_start(self.session.date),
            section=self.section,
            notes='Plan fijo para reactivar por reconciliacion',
        ).assign_weekly_slots([slot])
        historical_booking = Booking.objects.create(
            session=self.session,
            student=self.student,
            status=BookingStatus.CANCELLED,
            source=BookingSource.FIXED_SLOT,
            cancelled_at=timezone.now(),
            cancelled_by=self.student,
        )

        with self.assertRaisesMessage(ValidationError, 'booking history for this fixed plan session'):
            Booking.objects.create_booking(session=self.session, student=self.student)

        new_booking = Booking.objects.create_booking(
            session=self.session,
            student=self.student,
            allow_fixed_plan_history=True,
        )

        self.assertEqual(historical_booking.status, BookingStatus.CANCELLED)
        self.assertEqual(new_booking.status, BookingStatus.BOOKED)
        self.assertEqual(new_booking.source, BookingSource.FIXED_SLOT)
        self.assertEqual(Booking.objects.filter(session=self.session, student=self.student).count(), 2)

class StudentBookingUseCaseTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.student = User.objects.create_user(
            email='use-case-student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 4, 20),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )

    def test_create_booking_returns_booking_context(self):
        reservation = create_booking(session_id=self.session.pk, student=self.student)

        self.assertEqual(reservation.session.pk, self.session.pk)
        self.assertEqual(reservation.booking.student, self.student)
        self.assertEqual(reservation.booking.status, BookingStatus.BOOKED)
        self.assertIsNone(reservation.recovery_credit)

    def test_create_booking_marks_recovery_credit_as_used(self):
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=self.student,
            section=self.section,
            reference_date=self.session.date,
        )

        reservation = create_booking(
            session_id=self.session.pk,
            student=self.student,
            used_recovery_credit_id=recovery_credit.pk,
        )

        recovery_credit.refresh_from_db()
        self.assertEqual(reservation.booking.source, BookingSource.MAKEUP)
        self.assertEqual(reservation.recovery_credit.pk, recovery_credit.pk)
        self.assertEqual(reservation.recovery_credit.status, RecoveryCreditStatus.USED)
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.USED)

    def test_create_booking_rejects_missing_student_recovery_credit(self):
        with self.assertRaisesMessage(ValidationError, 'Recovery credit is not available for this student.'):
            create_booking(session_id=self.session.pk, student=self.student, used_recovery_credit_id=999999)

    def test_cancel_booking_returns_booking_and_generated_recovery(self):
        start_at = timezone.now() + timedelta(days=4)
        local_start = timezone.localtime(start_at)
        session = ClassSession.objects.create(
            section=self.section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=(local_start + timedelta(hours=1)).time().replace(tzinfo=None),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        if normalize_month_start(session.date) != normalize_month_start(self.session.date):
            MonthlyAccessStatus.objects.create(
                student=self.student,
                month=session.date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )
        booking = Booking.objects.create_booking(session=session, student=self.student)

        cancellation = cancel_booking(
            booking_id=booking.pk,
            student=self.student,
            actor=self.student,
            when=start_at - timedelta(hours=3),
        )

        booking.refresh_from_db()
        self.assertEqual(cancellation.booking.pk, booking.pk)
        self.assertEqual(cancellation.booking.status, BookingStatus.CANCELLED)
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertEqual(cancellation.recovery_credit.student, self.student)
        self.assertEqual(cancellation.recovery_credit.origin_session, session)

    def test_mark_booking_attended_returns_updated_booking_without_repeating_domain_rules(self):
        mark_time = timezone.now()
        start_at = mark_time - timedelta(minutes=30)
        local_start = timezone.localtime(start_at)
        session = ClassSession.objects.create(
            section=self.section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=(local_start + timedelta(hours=1)).time().replace(tzinfo=None),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        if normalize_month_start(session.date) != normalize_month_start(self.session.date):
            MonthlyAccessStatus.objects.create(
                student=self.student,
                month=session.date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )
        booking = Booking.objects.create_booking(session=session, student=self.student)

        result = mark_booking_attended(booking_id=booking.pk, when=mark_time)

        booking.refresh_from_db()
        self.assertEqual(result.booking.pk, booking.pk)
        self.assertEqual(result.booking.status, BookingStatus.ATTENDED)
        self.assertEqual(booking.status, BookingStatus.ATTENDED)
        self.assertEqual(result.booking.attendance_marked_at, booking.attendance_marked_at)

    def test_mark_booking_no_show_returns_updated_booking_after_session_end(self):
        mark_time = timezone.now()
        end_at = mark_time - timedelta(minutes=10)
        local_start = timezone.localtime(end_at - timedelta(hours=1))
        session = ClassSession.objects.create(
            section=self.section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=timezone.localtime(end_at).time().replace(tzinfo=None),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        if normalize_month_start(session.date) != normalize_month_start(self.session.date):
            MonthlyAccessStatus.objects.create(
                student=self.student,
                month=session.date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )
        booking = Booking.objects.create_booking(session=session, student=self.student)

        result = mark_booking_no_show(booking_id=booking.pk, when=mark_time)

        booking.refresh_from_db()
        self.assertEqual(result.booking.pk, booking.pk)
        self.assertEqual(result.booking.status, BookingStatus.NO_SHOW)
        self.assertEqual(booking.status, BookingStatus.NO_SHOW)

    def test_mark_booking_attended_propagates_domain_validation_for_future_sessions(self):
        mark_time = timezone.now()
        start_at = mark_time + timedelta(hours=3)
        local_start = timezone.localtime(start_at)
        session = ClassSession.objects.create(
            section=self.section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=(local_start + timedelta(hours=1)).time().replace(tzinfo=None),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        if normalize_month_start(session.date) != normalize_month_start(self.session.date):
            MonthlyAccessStatus.objects.create(
                student=self.student,
                month=session.date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )
        booking = Booking.objects.create_booking(session=session, student=self.student)

        with self.assertRaisesMessage(ValidationError, 'Attendance cannot be marked before the class starts.'):
            mark_booking_attended(booking_id=booking.pk, when=mark_time)

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.BOOKED)

class BookingCancellationAndRecoveryTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.student = User.objects.create_user(
            email='student-stage3@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.other_student = User.objects.create_user(
            email='student-other-stage3@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.other_section,
        )
        self.admin_user = User.objects.create_user(
            email='admin-stage3@example.com',
            password='secret123',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True,
        )

    def grant_access(self, student, target_date):
        return MonthlyAccessStatus.objects.create(
            student=student,
            month=target_date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )

    def create_session(self, *, section, start_at, capacity=4):
        local_start = timezone.localtime(start_at)
        return ClassSession.objects.create(
            section=section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=(local_start + timedelta(hours=1)).time().replace(tzinfo=None),
            capacity=capacity,
            status=SessionStatus.SCHEDULED,
        )

    def test_valid_cancellation_generates_recovery(self):
        start_at = timezone.now() + timedelta(days=2)
        session = self.create_session(section=self.section, start_at=start_at)
        self.grant_access(self.student, session.date)
        booking = Booking.objects.create_booking(session=session, student=self.student)

        recovery_credit = booking.cancel_by_student(actor=self.student, when=start_at - timedelta(hours=3))

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertTrue(booking.cancellation_generates_recovery)
        self.assertEqual(session.active_bookings().count(), 0)
        self.assertEqual(recovery_credit.source, RecoveryCreditSource.TIMELY_CANCELLATION)
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertEqual(recovery_credit.origin_session, session)
        self.assertEqual(recovery_credit.expires_at, recovery_credit.calculate_expiration_date(reference_date=session.date))

    def test_late_cancellation_is_rejected(self):
        start_at = timezone.now() + timedelta(hours=1, minutes=30)
        session = self.create_session(section=self.section, start_at=start_at)
        self.grant_access(self.student, session.date)
        booking = Booking.objects.create_booking(session=session, student=self.student)

        with self.assertRaisesMessage(ValidationError, 'more than 2 hours before class start'):
            booking.cancel_by_student(actor=self.student, when=timezone.now())

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertFalse(RecoveryCredit.objects.filter(student=self.student).exists())

    def test_exact_two_hour_cancellation_is_rejected(self):
        start_at = timezone.now() + timedelta(days=2)
        session = self.create_session(section=self.section, start_at=start_at)
        self.grant_access(self.student, session.date)
        booking = Booking.objects.create_booking(session=session, student=self.student)

        with self.assertRaisesMessage(ValidationError, 'more than 2 hours before class start'):
            booking.cancel_by_student(actor=self.student, when=start_at - timedelta(hours=2))

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertFalse(RecoveryCredit.objects.filter(student=self.student).exists())

    def test_using_recovery_on_same_activity_marks_credit_as_used(self):
        start_at = timezone.now() + timedelta(days=4)
        session = self.create_session(section=self.section, start_at=start_at)
        self.grant_access(self.student, session.date)
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=self.student,
            section=self.section,
            granted_by=self.admin_user,
            reference_date=timezone.localdate(),
        )

        booking = Booking.objects.create_booking(
            session=session,
            student=self.student,
            used_recovery_credit=recovery_credit,
        )

        recovery_credit.refresh_from_db()
        self.assertEqual(booking.source, 'makeup')
        self.assertEqual(booking.used_recovery_credit, recovery_credit)
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.USED)
        self.assertIsNotNone(recovery_credit.used_at)

    def test_cadillac_recovery_can_be_used_on_reformer(self):
        start_at = timezone.now() + timedelta(days=5)
        session = self.create_session(section=self.other_section, start_at=start_at)
        self.grant_access(self.other_student, session.date)
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=self.other_student,
            section=self.section,
            granted_by=self.admin_user,
            reference_date=timezone.localdate(),
        )

        booking = Booking.objects.create_booking(
            session=session,
            student=self.other_student,
            used_recovery_credit=recovery_credit,
        )

        recovery_credit.refresh_from_db()
        self.assertEqual(booking.used_recovery_credit, recovery_credit)
        self.assertEqual(booking.source, 'makeup')
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.USED)

    def test_reformer_recovery_on_different_activity_is_rejected(self):
        start_at = timezone.now() + timedelta(days=5)
        session = self.create_session(section=self.section, start_at=start_at)
        self.student.primary_section = self.other_section
        self.student.save(update_fields=['primary_section', 'updated_at'])
        self.grant_access(self.student, session.date)
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=self.student,
            section=self.other_section,
            granted_by=self.admin_user,
            reference_date=timezone.localdate(),
        )

        with self.assertRaisesMessage(ValidationError, 'compatible with this section'):
            Booking.objects.create_booking(
                session=session,
                student=self.student,
                used_recovery_credit=recovery_credit,
            )

        recovery_credit.refresh_from_db()
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertIsNone(recovery_credit.used_at)

    def test_using_recovery_on_original_session_is_allowed(self):
        start_at = timezone.now() + timedelta(days=6)
        session = self.create_session(section=self.section, start_at=start_at)
        self.grant_access(self.student, session.date)
        recovery_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.TIMELY_CANCELLATION,
            status=RecoveryCreditStatus.AVAILABLE,
            origin_session=session,
            expires_at=date(2026, 12, 31),
        )

        booking = Booking.objects.create_booking(
            session=session,
            student=self.student,
            used_recovery_credit=recovery_credit,
        )

        recovery_credit.refresh_from_db()
        self.assertEqual(booking.session, session)
        self.assertEqual(booking.student, self.student)
        self.assertEqual(booking.source, BookingSource.MAKEUP)
        self.assertEqual(booking.used_recovery_credit, recovery_credit)
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.USED)
        self.assertIsNotNone(recovery_credit.used_at)

    def test_admin_manual_grant_creates_available_recovery_credit(self):
        session = self.create_session(section=self.section, start_at=timezone.now() + timedelta(days=7))
        form = RecoveryCreditAdminForm(
            data={
                'student': self.student.pk,
                'section': self.section.pk,
                'origin_session': session.pk,
                'notes': 'Exceptional grant',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        recovery_credit = form.save(granted_by=self.admin_user)

        self.assertEqual(recovery_credit.source, RecoveryCreditSource.MANUAL)
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertEqual(recovery_credit.granted_by, self.admin_user)
        self.assertEqual(recovery_credit.origin_session, session)
        self.assertEqual(recovery_credit.expires_at, recovery_credit.calculate_expiration_date(reference_date=session.date))

class BookingMoveLifecycleTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.student = User.objects.create_user(
            email='move-student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.other_student = User.objects.create_user(
            email='move-other@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
        )
        self.admin_user = User.objects.create_user(
            email='move-admin@example.com',
            password='secret123',
            first_name='Admin',
            last_name='Operator',
            role='admin',
            is_staff=True,
        )

    def grant_access(self, student, target_date):
        return MonthlyAccessStatus.objects.create(
            student=student,
            month=target_date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )

    def create_session(self, *, target_date, start_hour, status=SessionStatus.SCHEDULED, capacity=4):
        return ClassSession.objects.create(
            section=self.section,
            date=target_date,
            start_time=time(start_hour, 0),
            end_time=time(start_hour + 1, 0),
            capacity=capacity,
            status=status,
        )

    def test_move_to_session_marks_original_as_moved_and_creates_traced_booking(self):
        original_session = self.create_session(target_date=date(2026, 6, 10), start_hour=9)
        target_session = self.create_session(target_date=date(2026, 6, 12), start_hour=10)
        self.grant_access(self.student, original_session.date)
        booking = Booking.objects.create_booking(session=original_session, student=self.student)

        moved_booking = booking.move_to_session(target_session=target_session, actor=self.admin_user)

        booking.refresh_from_db()
        moved_booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.MOVED)
        self.assertEqual(booking.moved_to_session, target_session)
        self.assertEqual(moved_booking.moved_from_booking, booking)
        self.assertEqual(moved_booking.status, BookingStatus.BOOKED)
        self.assertEqual(moved_booking.source, booking.source)
        self.assertEqual(original_session.active_bookings().count(), 0)
        self.assertEqual(target_session.active_bookings().count(), 1)

        audit_log = AuditLog.objects.get(entity_type='Booking', entity_id=booking.pk, action=AuditAction.MOVE)
        self.assertEqual(audit_log.actor, self.admin_user)
        self.assertEqual(audit_log.payload['to_booking_id'], moved_booking.pk)
        self.assertEqual(audit_log.payload['to_session_id'], target_session.pk)

    def test_move_to_session_rejects_inactive_original_booking(self):
        original_session = self.create_session(target_date=date(2026, 6, 10), start_hour=9)
        target_session = self.create_session(target_date=date(2026, 6, 12), start_hour=10)
        self.grant_access(self.student, original_session.date)
        booking = Booking.objects.create_booking(session=original_session, student=self.student)
        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=['status', 'updated_at'])

        with self.assertRaisesMessage(ValidationError, 'Only active bookings can be moved.'):
            booking.move_to_session(target_session=target_session)

    def test_move_to_session_reuses_target_validation_for_closed_session(self):
        original_session = self.create_session(target_date=date(2026, 6, 10), start_hour=9)
        target_session = self.create_session(
            target_date=date(2026, 6, 12),
            start_hour=10,
            status=SessionStatus.CANCELLED,
        )
        self.grant_access(self.student, original_session.date)
        booking = Booking.objects.create_booking(session=original_session, student=self.student)

        with self.assertRaisesMessage(ValidationError, 'cannot be booked'):
            booking.move_to_session(target_session=target_session)

    def test_move_to_session_reuses_target_validation_for_capacity_and_duplicates(self):
        original_session = self.create_session(target_date=date(2026, 6, 10), start_hour=9)
        full_session = self.create_session(target_date=date(2026, 6, 12), start_hour=10, capacity=1)
        duplicate_session = self.create_session(target_date=date(2026, 6, 14), start_hour=11, capacity=3)
        self.grant_access(self.student, original_session.date)
        self.grant_access(self.other_student, full_session.date)
        booking = Booking.objects.create_booking(session=original_session, student=self.student)
        Booking.objects.create_booking(session=full_session, student=self.other_student)
        Booking.objects.create_booking(session=duplicate_session, student=self.student)

        with self.assertRaisesMessage(ValidationError, 'reached its capacity'):
            booking.move_to_session(target_session=full_session)

        with self.assertRaisesMessage(ValidationError, 'already has an active booking'):
            booking.move_to_session(target_session=duplicate_session)

    def test_move_to_session_requires_operational_access_for_target_month(self):
        original_session = self.create_session(target_date=date(2026, 6, 10), start_hour=9)
        target_session = self.create_session(target_date=date(2026, 7, 12), start_hour=10)
        self.grant_access(self.student, original_session.date)
        booking = Booking.objects.create_booking(session=original_session, student=self.student)

        with self.assertRaisesMessage(ValidationError, 'active monthly operational access'):
            booking.move_to_session(target_session=target_session)

    def test_move_to_session_allows_cross_month_grace_window_without_new_month_access(self):
        original_session = self.create_session(target_date=date(2026, 6, 27), start_hour=9)
        target_session = self.create_session(target_date=date(2026, 7, 1), start_hour=10)
        self.grant_access(self.student, original_session.date)
        MonthlyAccessStatus.objects.filter(student=self.student, month=date(2026, 7, 1)).delete()
        booking = Booking.objects.create_booking(session=original_session, student=self.student)

        moved_booking = booking.move_to_session(target_session=target_session, actor=self.admin_user)

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.MOVED)
        self.assertEqual(moved_booking.session, target_session)
        self.assertEqual(moved_booking.status, BookingStatus.BOOKED)

    def test_move_to_session_preserves_used_recovery_credit_for_makeup_booking(self):
        original_session = self.create_session(target_date=date(2026, 6, 10), start_hour=9)
        target_session = self.create_session(target_date=date(2026, 6, 12), start_hour=10)
        self.grant_access(self.student, original_session.date)
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=self.student,
            section=self.section,
            granted_by=self.admin_user,
            reference_date=original_session.date,
        )
        booking = Booking.objects.create_booking(
            session=original_session,
            student=self.student,
            used_recovery_credit=recovery_credit,
        )

        moved_booking = booking.move_to_session(target_session=target_session, actor=self.admin_user)

        recovery_credit.refresh_from_db()
        self.assertEqual(moved_booking.source, BookingSource.MAKEUP)
        self.assertEqual(moved_booking.used_recovery_credit, recovery_credit)
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.USED)

    def test_moved_status_requires_different_destination_session(self):
        original_session = self.create_session(target_date=date(2026, 6, 10), start_hour=9)
        self.grant_access(self.student, original_session.date)
        booking = Booking.objects.create_booking(session=original_session, student=self.student)

        booking.status = BookingStatus.MOVED
        booking.moved_to_session = original_session

        with self.assertRaisesMessage(ValidationError, 'different destination session'):
            booking.full_clean()

class BookingAttendanceLifecycleTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.student = User.objects.create_user(
            email='attendance-student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )

    def create_booking(self, *, start_at, end_at=None, session_status=SessionStatus.SCHEDULED):
        local_start = timezone.localtime(start_at)
        local_end = timezone.localtime(end_at or (start_at + timedelta(hours=1)))
        session = ClassSession.objects.create(
            section=self.section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=local_end.time().replace(tzinfo=None),
            capacity=4,
            status=session_status,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        return Booking.objects.create_booking(session=session, student=self.student)

    def test_mark_attended_updates_active_booking_after_session_starts(self):
        start_at = timezone.now() - timedelta(minutes=30)
        booking = self.create_booking(start_at=start_at)

        updated_booking = booking.mark_attended(when=timezone.now())

        booking.refresh_from_db()
        self.assertEqual(updated_booking.pk, booking.pk)
        self.assertEqual(booking.status, BookingStatus.ATTENDED)
        self.assertIsNotNone(booking.attendance_marked_at)

    def test_mark_attended_rejects_future_session(self):
        start_at = timezone.now() + timedelta(hours=3)
        booking = self.create_booking(start_at=start_at)

        with self.assertRaisesMessage(ValidationError, 'Attendance cannot be marked before the class starts.'):
            booking.mark_attended(when=timezone.now())

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertIsNone(booking.attendance_marked_at)

    def test_mark_no_show_requires_session_to_end(self):
        start_at = timezone.now() - timedelta(minutes=15)
        booking = self.create_booking(start_at=start_at, end_at=timezone.now() + timedelta(minutes=45))

        with self.assertRaisesMessage(ValidationError, 'A no-show can only be marked after the class ends.'):
            booking.mark_no_show(when=timezone.now())

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.BOOKED)

    def test_mark_no_show_updates_active_booking_after_session_ends(self):
        end_at = timezone.now() - timedelta(minutes=10)
        booking = self.create_booking(start_at=end_at - timedelta(hours=1), end_at=end_at)

        booking.mark_no_show(when=timezone.now())

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.NO_SHOW)
        self.assertIsNotNone(booking.attendance_marked_at)

    def test_attendance_marking_rejects_non_scheduled_sessions(self):
        start_at = timezone.now() - timedelta(hours=1)
        booking = self.create_booking(start_at=start_at, session_status=SessionStatus.SCHEDULED)
        booking.session.status = SessionStatus.HOLIDAY_CLOSED
        booking.session.save(update_fields=['status', 'updated_at'])

        with self.assertRaisesMessage(ValidationError, 'Only scheduled sessions can have attendance marked.'):
            booking.mark_attended(when=timezone.now())

    def test_attendance_marking_rejects_inactive_booking(self):
        start_at = timezone.now() - timedelta(hours=3)
        booking = self.create_booking(start_at=start_at)
        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=['status', 'updated_at'])

        with self.assertRaisesMessage(ValidationError, 'Only active bookings can be marked for attendance.'):
            booking.mark_attended(when=timezone.now())

class BookingStateMachineTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.student = User.objects.create_user(
            email='state-machine-student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.admin_user = User.objects.create_user(
            email='state-machine-admin@example.com',
            password='secret123',
            first_name='Admin',
            last_name='Operator',
            role='admin',
            is_staff=True,
        )

    def grant_access(self, target_date):
        return MonthlyAccessStatus.objects.create(
            student=self.student,
            month=target_date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )

    def create_session(self, *, start_at, end_at=None, status=SessionStatus.SCHEDULED):
        local_start = timezone.localtime(start_at)
        local_end = timezone.localtime(end_at or (start_at + timedelta(hours=1)))
        return ClassSession.objects.create(
            section=self.section,
            date=local_start.date(),
            start_time=local_start.time().replace(tzinfo=None),
            end_time=local_end.time().replace(tzinfo=None),
            capacity=4,
            status=status,
        )

    def create_booking(self, *, start_at, end_at=None):
        session = self.create_session(start_at=start_at, end_at=end_at)
        self.grant_access(session.date)
        return Booking.objects.create_booking(session=session, student=self.student)

    def assert_status_transition_error(self, booking, target_status):
        booking.status = target_status

        with self.assertRaises(ValidationError) as exc:
            booking.full_clean()

        self.assertIn('status', exc.exception.message_dict)
        self.assertIn('Invalid booking transition', exc.exception.message_dict['status'][0])

    def test_booked_exposes_all_domain_allowed_transitions(self):
        booking = self.create_booking(start_at=timezone.now() + timedelta(days=3))

        self.assertEqual(
            booking.available_status_transitions(),
            {
                BookingStatus.CANCELLED,
                BookingStatus.ATTENDED,
                BookingStatus.NO_SHOW,
                BookingStatus.MOVED,
            },
        )

    def test_cancelled_booking_cannot_transition_to_attended(self):
        start_at = timezone.now() + timedelta(days=3)
        booking = self.create_booking(start_at=start_at)
        booking.cancel_by_student(actor=self.student, when=start_at - timedelta(hours=3))

        booking.cancelled_at = None
        booking.cancelled_by = None
        booking.cancellation_generates_recovery = False
        booking.attendance_marked_at = timezone.now()

        self.assert_status_transition_error(booking, BookingStatus.ATTENDED)

    def test_attended_booking_cannot_transition_to_no_show(self):
        booking = self.create_booking(start_at=timezone.now() - timedelta(hours=2))
        booking.mark_attended(when=timezone.now())

        self.assert_status_transition_error(booking, BookingStatus.NO_SHOW)

    def test_moved_booking_cannot_transition_to_cancelled(self):
        original_session = self.create_session(start_at=timezone.now() + timedelta(days=2))
        target_session = self.create_session(start_at=timezone.now() + timedelta(days=4))
        self.grant_access(original_session.date)
        booking = Booking.objects.create_booking(session=original_session, student=self.student)

        booking.move_to_session(target_session=target_session, actor=self.admin_user)
        booking.refresh_from_db()
        booking.moved_to_session = None

        self.assert_status_transition_error(booking, BookingStatus.CANCELLED)
