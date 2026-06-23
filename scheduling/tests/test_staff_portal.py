from django.template import engines

from ._shared import *

class MonthlyAccessAdminActionTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.staff_user = User.objects.create_user(
            email='monthly-access-admin@example.com',
            password='AdminSecret2026!',
            first_name='Grace',
            last_name='Hopper',
            role='admin',
            is_staff=True,
            primary_section=self.section,
        )
        self.student = User.objects.create_user(
            email='monthly-access-student@example.com',
            password='StudentSecret2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.month = normalize_month_start(timezone.localdate())
        self.admin_site = AdminSite()
        self.model_admin = MonthlyAccessStatusAdmin(MonthlyAccessStatus, self.admin_site)
        self.messages = []
        self.model_admin.message_user = lambda _request, message: self.messages.append(message)

    def test_activate_access_action_uses_monthly_access_use_case_and_records_audit(self):
        access = MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.month,
            status=MonthlyAccessStatusType.PENDING_PAYMENT,
            booking_enabled=False,
        )
        request = HttpRequest()
        request.user = self.staff_user

        activate_access_by_payment(self.model_admin, request, MonthlyAccessStatus.objects.filter(pk=access.pk))

        access.refresh_from_db()
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertEqual(access.activated_by, self.staff_user)
        audit_log = AuditLog.objects.get(entity_type='MonthlyAccessStatus', entity_id=access.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['status'], MonthlyAccessStatusType.ACTIVE)
        self.assertEqual(
            self.messages,
            ['Se activaron 1 accesos mensuales. Sin cambios: 0.'],
        )

    def test_suspend_access_action_uses_monthly_access_use_case_and_records_audit(self):
        access = MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.month,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        request = HttpRequest()
        request.user = self.staff_user

        suspend_operational_access(self.model_admin, request, MonthlyAccessStatus.objects.filter(pk=access.pk))

        access.refresh_from_db()
        self.assertEqual(access.status, MonthlyAccessStatusType.SUSPENDED)
        self.assertFalse(access.booking_enabled)
        audit_log = AuditLog.objects.get(entity_type='MonthlyAccessStatus', entity_id=access.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['status'], MonthlyAccessStatusType.SUSPENDED)
        self.assertEqual(
            self.messages,
            ['Se suspendieron 1 accesos mensuales. Sin cambios: 0.'],
        )


class RecoveryCreditAdminActionTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.staff_user = User.objects.create_user(
            email='recovery-admin@example.com',
            password='AdminSecret2026!',
            first_name='Grace',
            last_name='Hopper',
            role='admin',
            is_staff=True,
            primary_section=self.section,
        )
        self.student = User.objects.create_user(
            email='recovery-student@example.com',
            password='StudentSecret2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.today = timezone.localdate()
        self.admin_site = AdminSite()
        self.model_admin = RecoveryCreditAdmin(RecoveryCredit, self.admin_site)
        self.messages = []
        self.model_admin.message_user = lambda _request, message: self.messages.append(message)

    def test_expire_overdue_action_uses_application_layer_and_records_audit(self):
        overdue_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today - timedelta(days=3),
        )
        current_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today + timedelta(days=7),
        )
        request = HttpRequest()
        request.user = self.staff_user

        expire_overdue_recovery_credits(
            self.model_admin,
            request,
            RecoveryCredit.objects.filter(pk__in=[overdue_credit.pk, current_credit.pk]).order_by('pk'),
        )

        overdue_credit.refresh_from_db()
        current_credit.refresh_from_db()
        self.assertEqual(overdue_credit.status, RecoveryCreditStatus.EXPIRED)
        self.assertEqual(current_credit.status, RecoveryCreditStatus.AVAILABLE)
        audit_log = AuditLog.objects.get(entity_type='RecoveryCredit', entity_id=overdue_credit.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['reason'], 'overdue')
        self.assertEqual(
            self.messages,
            ['Se marcaron 1 recuperaciones como vencidas. Sin cambios: 1.'],
        )

class HolidayClosureAdminTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.staff_user = User.objects.create_user(
            email='holiday-admin@example.com',
            password='AdminSecret2026!',
            first_name='Grace',
            last_name='Hopper',
            role='admin',
            is_staff=True,
            primary_section=self.section,
        )
        self.student = User.objects.create_user(
            email='holiday-admin-student@example.com',
            password='StudentSecret2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.admin_site = AdminSite()
        self.model_admin = HolidayClosureAdmin(HolidayClosure, self.admin_site)
        self.messages = []
        self.model_admin.message_user = lambda _request, message: self.messages.append(message)

    def test_save_model_uses_holiday_closure_use_case_and_records_create_audit(self):
        closure_date = timezone.localdate() + timedelta(days=5)
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=normalize_month_start(closure_date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        session = ClassSession.objects.create(
            section=self.section,
            date=closure_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=session, student=self.student)
        request = HttpRequest()
        request.user = self.staff_user
        obj = HolidayClosure(date=closure_date, reason='Feriado admin', notes='Se cierra desde admin')

        self.model_admin.save_model(request, obj, form=None, change=False)

        closure = HolidayClosure.objects.get(date=closure_date)
        session.refresh_from_db()
        self.assertEqual(obj.pk, closure.pk)
        self.assertEqual(closure.created_by, self.staff_user)
        self.assertEqual(session.status, SessionStatus.HOLIDAY_CLOSED)
        audit_log = AuditLog.objects.get(entity_type='HolidayClosure', entity_id=closure.pk)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.action, AuditAction.CREATE)
        self.assertEqual(audit_log.payload['created_credits'], 1)
        self.assertEqual(
            self.messages,
            [
                (
                    f'Feriado aplicado para {closure_date}: '
                    '1 sesiones actualizadas, '
                    '1 recuperaciones creadas, '
                    '0 recuperaciones ya existentes.'
                )
            ],
        )

    def test_action_reapplies_existing_closure_and_records_update_audit(self):
        closure_date = timezone.localdate() + timedelta(days=7)
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=normalize_month_start(closure_date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        session = ClassSession.objects.create(
            section=self.section,
            date=closure_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=session, student=self.student)
        closure = HolidayClosure.objects.create(date=closure_date, reason='Feriado ya cargado', created_by=self.staff_user)
        request = HttpRequest()
        request.user = self.staff_user

        apply_holiday_closures(self.model_admin, request, HolidayClosure.objects.filter(pk=closure.pk))

        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.HOLIDAY_CLOSED)
        audit_log = AuditLog.objects.get(entity_type='HolidayClosure', entity_id=closure.pk)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.action, AuditAction.UPDATE)
        self.assertEqual(audit_log.payload['updated_sessions'], 1)
        self.assertEqual(audit_log.payload['created_credits'], 1)
        self.assertEqual(
            self.messages,
            [
                'Se aplicaron 1 feriados. '
                'Sesiones actualizadas: 1. '
                'Recuperaciones nuevas: 1. '
                'Recuperaciones ya existentes: 0.'
            ],
        )

class AdminPortalViewTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.today = timezone.localdate()
        self.current_month = date(self.today.year, self.today.month, 1)
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='StaffPortal2026!',
            first_name='Admin',
            last_name='Operator',
            role='admin',
            is_staff=True,
            must_change_password=False,
        )
        self.staff_user.temporary_password_set_at = None
        self.staff_user.save(update_fields=['temporary_password_set_at', 'updated_at'])
        self.active_student = User.objects.create_user(
            email='ada@example.com',
            password='StudentPass2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
            must_change_password=False,
        )
        self.pending_student = User.objects.create_user(
            email='grace@example.com',
            password='StudentPass2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.other_section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=self.active_student,
            month=self.current_month,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        MonthlyAccessStatus.objects.create(
            student=self.pending_student,
            month=self.current_month,
            status=MonthlyAccessStatusType.PENDING_PAYMENT,
            booking_enabled=False,
        )
        self.upcoming_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        self.other_upcoming_session = ClassSession.objects.create(
            section=self.other_section,
            date=self.today + timedelta(days=3),
            start_time=time(16, 0),
            end_time=time(17, 0),
            capacity=5,
            status=SessionStatus.SCHEDULED,
        )
        self.cancelled_session = ClassSession.objects.create(
            section=self.section,
            date=self.today - timedelta(days=4),
            start_time=time(11, 0),
            end_time=time(12, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=self.upcoming_session, student=self.active_student)
        Booking.objects.create(
            session=self.cancelled_session,
            student=self.active_student,
            status=BookingStatus.CANCELLED,
            source='manual',
            cancellation_generates_recovery=True,
        )
        RecoveryCredit.objects.create(
            student=self.active_student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today + timedelta(days=21),
        )
        RecoveryCredit.objects.create(
            student=self.active_student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.EXPIRED,
            expires_at=self.today - timedelta(days=3),
        )

    def test_staff_labels_tag_library_loads_for_staff_templates(self):
        template = engines['django'].from_string('{% load staff_labels %}{{ value|staff_session_status_label }}')

        rendered = template.render({'value': SessionStatus.SCHEDULED})

        self.assertEqual(rendered, 'Programada')

    def test_staff_labels_library_exports_template_filter_aliases(self):
        template = engines['django'].from_string(
            '{% load staff_labels %}'
            '{{ booking|booking_status_label }}|'
            '{{ session|session_status_label }}|'
            '{{ recovery|recovery_source_label }}'
        )

        rendered = template.render(
            {
                'booking': BookingStatus.CANCELLED,
                'session': SessionStatus.HOLIDAY_CLOSED,
                'recovery': RecoveryCreditSource.MANUAL,
            }
        )

        self.assertEqual(rendered, 'Cancelada|Cerrada por feriado|carga manual')

    def test_admin_portal_requires_login(self):
        response = self.client.get(reverse('admin-student-list'))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('admin-student-list')}")

    def test_non_staff_user_gets_forbidden(self):
        self.client.force_login(self.active_student)

        response = self.client.get(reverse('admin-student-list'))

        self.assertEqual(response.status_code, 403)

    def test_admin_detail_requires_login(self):
        response = self.client.get(reverse('admin-student-detail', args=[self.active_student.pk]))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('admin-student-detail', args=[self.active_student.pk])}",
        )

    def test_admin_detail_forbids_non_staff_user(self):
        self.client.force_login(self.active_student)

        response = self.client.get(reverse('admin-student-detail', args=[self.active_student.pk]))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_search_students_and_see_operational_payment_state(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin-student-list'), {'q': 'ada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, self.section.name)
        self.assertContains(response, 'Al día')
        self.assertNotContains(response, 'Grace Hopper')

    def test_staff_list_uses_state_specific_monthly_access_ctas(self):
        suspended_student = User.objects.create_user(
            email='hedy@example.com',
            password='StudentPass2026!',
            first_name='Hedy',
            last_name='Lamarr',
            primary_section=self.section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=suspended_student,
            month=self.current_month,
            status=MonthlyAccessStatusType.SUSPENDED,
            booking_enabled=False,
        )
        student_without_status = User.objects.create_user(
            email='katherine@example.com',
            password='StudentPass2026!',
            first_name='Katherine',
            last_name='Johnson',
            primary_section=self.other_section,
            must_change_password=False,
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin-student-list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suspender acceso')
        self.assertContains(response, 'Registrar pago del mes')
        self.assertContains(response, 'Reactivar acceso')
        self.assertContains(response, 'Activar acceso del mes')
        self.assertContains(response, 'Ver detalle', count=4)

    def test_staff_list_links_to_student_detail(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin-student-list'), {'q': 'ada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin-student-detail', args=[self.active_student.pk]))

    def test_staff_can_view_student_detail_operational_snapshot(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin-student-detail', args=[self.active_student.pk]), {'q': 'ada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detalle de alumna')
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, self.active_student.email)
        self.assertContains(response, 'Sin teléfono cargado')
        self.assertContains(response, self.section.name)
        self.assertContains(response, 'Pago del mes')
        self.assertContains(response, 'Volver al listado')

    def test_staff_can_assign_monthly_plan_from_student_detail(self):
        slot_one = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        slot_two = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        self.client.force_login(self.staff_user)
        detail_url = f"{reverse('admin-student-detail', args=[self.active_student.pk])}?q=ada"

        response = self.client.post(
            reverse('admin-update-student-monthly-plan', args=[self.active_student.pk]),
            {
                'month': self.current_month.strftime('%Y-%m'),
                'slot_ids': [slot_one.pk, slot_two.pk],
                'notes': 'Plan fijo de junio',
                'q': 'ada',
                'next': detail_url,
            },
            follow=True,
        )

        plan = StudentMonthlyPlan.objects.get(student=self.active_student, month=self.current_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('admin-student-detail', args=[self.active_student.pk]))
        self.assertEqual(plan.section, self.section)
        self.assertEqual(plan.notes, 'Plan fijo de junio')
        self.assertEqual(list(plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')), [slot_one.pk, slot_two.pk])
        self.assertContains(response, 'Se actualizó el plan mensual de Ada Lovelace')
        self.assertContains(response, 'Plan mensual fijo')

    def test_staff_can_choose_month_and_save_plan_for_that_month(self):
        next_month = normalize_month_start(self.current_month + timedelta(days=32))
        slot_one = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.TUESDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_active=True,
        )
        slot_two = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.THURSDAY,
            start_time=time(18, 0),
            end_time=time(19, 0),
            is_active=True,
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('admin-student-detail', args=[self.active_student.pk]),
            {'q': 'ada', 'month': next_month.strftime('%Y-%m')},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{next_month:%Y-%m}"')
        self.assertContains(response, next_month.strftime('%m/%Y'))

        detail_url = f"{reverse('admin-student-detail', args=[self.active_student.pk])}?q=ada&month={next_month:%Y-%m}"
        response = self.client.post(
            reverse('admin-update-student-monthly-plan', args=[self.active_student.pk]),
            {
                'month': next_month.strftime('%Y-%m'),
                'slot_ids': [slot_one.pk, slot_two.pk],
                'notes': 'Plan fijo del mes siguiente',
                'q': 'ada',
                'next': detail_url,
            },
            follow=True,
        )

        plan = StudentMonthlyPlan.objects.get(student=self.active_student, month=next_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(plan.notes, 'Plan fijo del mes siguiente')
        self.assertEqual(list(plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')), [slot_one.pk, slot_two.pk])
        self.assertEqual(response.request['QUERY_STRING'], f'q=ada&month={next_month:%Y-%m}')
        self.assertContains(response, 'Plan fijo del mes siguiente')

    def test_staff_monthly_plan_rejects_more_than_three_slots(self):
        slots = [
            WeeklyClassSlot.objects.create(
                section=self.section,
                weekday=weekday,
                start_time=time(8 + index, 0),
                end_time=time(9 + index, 0),
                is_active=True,
            )
            for index, weekday in enumerate([Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY])
        ]
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-update-student-monthly-plan', args=[self.active_student.pk]),
            {
                'month': self.current_month.strftime('%Y-%m'),
                'slot_ids': [slot.pk for slot in slots],
                'notes': 'Demasiados horarios',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Solo podés elegir hasta 3 horarios para el plan mensual.')
        self.assertFalse(StudentMonthlyPlan.objects.filter(student=self.active_student, month=self.current_month).exists())

    def test_non_staff_user_cannot_update_monthly_plan(self):
        slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        self.client.force_login(self.active_student)

        response = self.client.post(
            reverse('admin-update-student-monthly-plan', args=[self.active_student.pk]),
            {'month': self.current_month.strftime('%Y-%m'), 'slot_ids': [slot.pk]},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(StudentMonthlyPlan.objects.filter(student=self.active_student, month=self.current_month).exists())

    def test_staff_can_grant_manual_recovery_from_detail(self):
        self.client.force_login(self.staff_user)
        detail_url = f"{reverse('admin-student-detail', args=[self.active_student.pk])}?q=ada"

        response = self.client.post(
            reverse('admin-grant-manual-recovery', args=[self.active_student.pk]),
            {
                'section': self.section.pk,
                'notes': 'Cortesia operativa',
                'q': 'ada',
                'next': detail_url,
            },
            follow=True,
        )

        credit = RecoveryCredit.objects.filter(student=self.active_student, notes='Cortesia operativa').get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('admin-student-detail', args=[self.active_student.pk]))
        self.assertEqual(credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertEqual(credit.source, RecoveryCreditSource.MANUAL)
        self.assertEqual(credit.granted_by, self.staff_user)
        audit_log = AuditLog.objects.get(entity_type='RecoveryCredit', entity_id=credit.pk, action=AuditAction.CREDIT)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['student_id'], self.active_student.pk)
        self.assertEqual(audit_log.payload['section_name'], self.section.name)
        self.assertEqual(audit_log.payload['status'], RecoveryCreditStatus.AVAILABLE)
        self.assertEqual(audit_log.payload['notes'], 'Cortesia operativa')
        self.assertContains(response, 'Se otorgo una recuperacion manual para Ada Lovelace')

    def test_staff_manual_recovery_ignores_unsafe_next_url(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-grant-manual-recovery', args=[self.active_student.pk]),
            {
                'section': self.section.pk,
                'notes': 'Next inseguro',
                'q': 'ada',
                'next': 'https://evil.example.com/phishing',
            },
        )

        credit = RecoveryCredit.objects.filter(student=self.active_student, notes='Next inseguro').get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('admin-student-detail', args=[self.active_student.pk])}?q=ada")
        self.assertEqual(credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertEqual(credit.granted_by, self.staff_user)

    def test_staff_manual_recovery_requires_valid_section(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-grant-manual-recovery', args=[self.active_student.pk]),
            {'notes': 'Sin actividad'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(RecoveryCredit.objects.filter(student=self.active_student, notes='Sin actividad').exists())

    def test_non_staff_user_cannot_manage_recoveries_from_detail(self):
        credit = RecoveryCredit.objects.filter(student=self.active_student, status=RecoveryCreditStatus.AVAILABLE).first()
        self.client.force_login(self.active_student)

        grant_response = self.client.post(
            reverse('admin-grant-manual-recovery', args=[self.active_student.pk]),
            {'section': self.section.pk},
        )
        expire_response = self.client.post(
            reverse('admin-expire-recovery-credit', args=[self.active_student.pk, credit.pk]),
        )

        self.assertEqual(grant_response.status_code, 403)
        self.assertEqual(expire_response.status_code, 403)

    def test_non_staff_user_cannot_create_holiday_closure(self):
        closure_date = self.today + timedelta(days=7)
        self.client.force_login(self.active_student)

        response = self.client.post(
            reverse('admin-create-holiday-closure'),
            {
                'date': closure_date.isoformat(),
                'reason': 'Intento no autorizado',
                'notes': 'No deberia persistir',
                'section': '',
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(HolidayClosure.objects.filter(date=closure_date).exists())

    def test_staff_can_mark_available_recovery_as_expired(self):
        credit = RecoveryCredit.objects.filter(student=self.active_student, status=RecoveryCreditStatus.AVAILABLE).first()
        self.client.force_login(self.staff_user)
        detail_url = f"{reverse('admin-student-detail', args=[self.active_student.pk])}?q=ada"

        response = self.client.post(
            reverse('admin-expire-recovery-credit', args=[self.active_student.pk, credit.pk]),
            {'q': 'ada', 'next': detail_url},
            follow=True,
        )

        credit.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('admin-student-detail', args=[self.active_student.pk]))
        self.assertEqual(credit.status, RecoveryCreditStatus.EXPIRED)
        self.assertEqual(credit.expires_at, self.today)
        audit_log = AuditLog.objects.get(entity_type='RecoveryCredit', entity_id=credit.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['student_id'], self.active_student.pk)
        self.assertEqual(audit_log.payload['status'], RecoveryCreditStatus.EXPIRED)
        self.assertEqual(audit_log.payload['section_name'], self.section.name)
        self.assertContains(response, 'Se marco como vencida la recuperacion de Ada Lovelace')

    def test_staff_cannot_manually_expire_used_recovery(self):
        used_credit = RecoveryCredit.objects.create(
            student=self.active_student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.USED,
            expires_at=self.today + timedelta(days=30),
            used_at=timezone.now(),
        )
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-expire-recovery-credit', args=[self.active_student.pk, used_credit.pk]),
            follow=True,
        )

        used_credit.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(used_credit.status, RecoveryCreditStatus.USED)
        self.assertContains(response, 'Solo se pueden marcar como vencidas las recuperaciones que siguen disponibles.')

    def test_staff_can_toggle_access_from_detail_and_stay_on_detail(self):
        self.client.force_login(self.staff_user)
        detail_url = f"{reverse('admin-student-detail', args=[self.active_student.pk])}?q=ada"

        response = self.client.post(
            reverse('admin-toggle-student-access', args=[self.active_student.pk]),
            {'q': 'ada', 'next': detail_url},
            follow=True,
        )

        access = self.active_student.get_monthly_access_for(self.current_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(access.status, MonthlyAccessStatusType.SUSPENDED)
        self.assertFalse(access.booking_enabled)
        audit_log = AuditLog.objects.get(entity_type='MonthlyAccessStatus', entity_id=access.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['student_id'], self.active_student.pk)
        self.assertEqual(audit_log.payload['status'], MonthlyAccessStatusType.SUSPENDED)
        self.assertFalse(audit_log.payload['booking_enabled'])
        self.assertEqual(response.request['PATH_INFO'], reverse('admin-student-detail', args=[self.active_student.pk]))
        self.assertContains(response, 'Se suspendio el acceso operativo de Ada Lovelace')
        self.assertContains(response, 'Bloqueado')

    def test_staff_can_suspend_current_month_access(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-toggle-student-access', args=[self.active_student.pk]),
            {'q': 'ada'},
            follow=True,
        )

        access = self.active_student.get_monthly_access_for(self.current_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(access.status, MonthlyAccessStatusType.SUSPENDED)
        self.assertFalse(access.booking_enabled)
        self.assertContains(response, 'Se suspendio el acceso operativo de Ada Lovelace')
        self.assertContains(response, 'Bloqueado')

    def test_staff_can_activate_student_without_current_month_access(self):
        student_without_status = User.objects.create_user(
            email='missing@example.com',
            password='StudentPass2026!',
            first_name='Katherine',
            last_name='Johnson',
            primary_section=self.section,
            must_change_password=False,
        )
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-toggle-student-access', args=[student_without_status.pk]),
            follow=True,
        )

        access = student_without_status.get_monthly_access_for(self.current_month)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(access)
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertEqual(access.activated_by, self.staff_user)
        audit_log = AuditLog.objects.get(entity_type='MonthlyAccessStatus', entity_id=access.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['student_id'], student_without_status.pk)
        self.assertEqual(audit_log.payload['status'], MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(audit_log.payload['booking_enabled'])
        self.assertContains(response, 'Se activo el acceso operativo de Katherine Johnson')

    def test_staff_can_mark_student_paid_and_activate_access(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-mark-student-paid', args=[self.pending_student.pk]),
            {'q': 'grace'},
            follow=True,
        )

        access = self.pending_student.get_monthly_access_for(self.current_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertEqual(access.activated_by, self.staff_user)
        audit_log = AuditLog.objects.get(entity_type='MonthlyAccessStatus', entity_id=access.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['status'], MonthlyAccessStatusType.ACTIVE)
        self.assertContains(response, 'Se registró el pago de Grace Hopper y el acceso quedó activo')

    def test_admin_class_agenda_requires_login(self):
        response = self.client.get(reverse('admin-class-agenda'))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('admin-class-agenda')}")

    def test_admin_class_agenda_forbids_non_staff_user(self):
        self.client.force_login(self.active_student)

        response = self.client.get(reverse('admin-class-agenda'))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_filter_class_agenda_by_section(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('admin-class-agenda'),
            {
                'date': self.today.isoformat(),
                'section': self.section.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clases habilitadas')
        self.assertContains(response, self.section.name)
        self.assertContains(response, self.upcoming_session.start_time.strftime('%H:%M'))
        self.assertNotContains(response, self.other_upcoming_session.start_time.strftime('%H:%M'))

    def test_staff_can_create_manual_class_session_from_agenda(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-create-class-session'),
            {
                'section': self.section.pk,
                'date': self.today.isoformat(),
                'start_time': '15:00',
                'end_time': '16:00',
                'capacity': 7,
                'section_filter': self.section.pk,
            },
            follow=True,
        )

        session = ClassSession.objects.get(section=self.section, date=self.today, start_time=time(15, 0))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(session.end_time, time(16, 0))
        self.assertEqual(session.capacity, 7)
        self.assertEqual(session.status, SessionStatus.SCHEDULED)
        self.assertContains(response, 'Se creó la clase de')
        self.assertContains(response, '15:00 - 16:00')

    def test_staff_cannot_create_duplicate_manual_class_session(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-create-class-session'),
            {
                'section': self.section.pk,
                'date': self.upcoming_session.date.isoformat(),
                'start_time': self.upcoming_session.start_time.strftime('%H:%M'),
                'end_time': self.upcoming_session.end_time.strftime('%H:%M'),
                'capacity': self.upcoming_session.capacity,
                'section_filter': self.section.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una clase para esa actividad en ese día y horario.')

    def test_staff_can_update_manual_class_session(self):
        manual_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=4),
            start_time=time(15, 0),
            end_time=time(16, 0),
            capacity=5,
            status=SessionStatus.SCHEDULED,
        )
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-update-class-session', args=[manual_session.pk]),
            {
                'section': self.other_section.pk,
                'date': manual_session.date.isoformat(),
                'start_time': '17:00',
                'end_time': '18:00',
                'capacity': 8,
            },
            follow=True,
        )

        manual_session.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(manual_session.section, self.other_section)
        self.assertEqual(manual_session.start_time, time(17, 0))
        self.assertEqual(manual_session.end_time, time(18, 0))
        self.assertEqual(manual_session.capacity, 8)
        self.assertContains(response, 'Se actualizó la clase de')

    def test_staff_can_delete_manual_class_session_without_bookings(self):
        manual_session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=5),
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=4,
            status=SessionStatus.SCHEDULED,
        )
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-delete-class-session', args=[manual_session.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClassSession.objects.filter(pk=manual_session.pk).exists())
        self.assertContains(response, 'Se eliminó la clase de')

    def test_staff_agenda_links_to_class_session_detail(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('admin-class-agenda'),
            {
                'date': self.today.isoformat(),
                'section': self.section.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'{reverse("admin-class-session-detail", args=[self.upcoming_session.pk])}?date={self.today.isoformat()}&amp;section={self.section.pk}',
        )

    def test_admin_class_session_detail_requires_login(self):
        response = self.client.get(reverse('admin-class-session-detail', args=[self.upcoming_session.pk]))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('admin-class-session-detail', args=[self.upcoming_session.pk])}",
        )

    def test_admin_class_session_detail_forbids_non_staff_user(self):
        self.client.force_login(self.active_student)

        response = self.client.get(reverse('admin-class-session-detail', args=[self.upcoming_session.pk]))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_class_session_detail_with_booking_context(self):
        makeup_student = User.objects.create_user(
            email='makeup@example.com',
            password='StudentPass2026!',
            first_name='Katherine',
            last_name='Johnson',
            primary_section=self.section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=makeup_student,
            month=normalize_month_start(self.upcoming_session.date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=makeup_student,
            section=self.section,
            granted_by=self.staff_user,
            reference_date=self.upcoming_session.date,
        )
        Booking.objects.create_booking(
            session=self.upcoming_session,
            student=makeup_student,
            used_recovery_credit=recovery_credit,
        )
        Booking.objects.create(
            session=self.upcoming_session,
            student=self.pending_student,
            status=BookingStatus.CANCELLED,
            source='manual',
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('admin-class-session-detail', args=[self.upcoming_session.pk]),
            {
                'date': self.today.isoformat(),
                'section': self.section.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detalle de clase')
        self.assertContains(response, self.section.name)
        self.assertContains(response, self.upcoming_session.date.strftime('%d/%m/%Y'))
        self.assertContains(response, 'Ocupacion actual')
        self.assertContains(response, '2 / 6')
        self.assertContains(response, 'Alumnas anotadas')
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, 'Katherine Johnson')
        self.assertContains(response, 'Reserva por recuperación manual')
        self.assertContains(response, 'Con recuperación')
        self.assertContains(response, 'Reservas recientes')
        self.assertContains(response, 'Grace Hopper')
        self.assertContains(response, 'Volver a la agenda')
        self.assertContains(
            response,
            f'{reverse("admin-class-agenda")}?date={self.today.isoformat()}&amp;section={self.section.pk}',
        )

    def test_staff_can_apply_holiday_closure_from_class_agenda(self):
        closure_date = self.today + timedelta(days=1)
        other_holiday_student = User.objects.create_user(
            email='holiday-other-portal@example.com',
            password='StudentPass2026!',
            first_name='Hedy',
            last_name='Lamarr',
            primary_section=self.other_section,
            must_change_password=False,
        )
        if normalize_month_start(closure_date) != self.current_month:
            MonthlyAccessStatus.objects.create(
                student=self.active_student,
                month=closure_date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )
            MonthlyAccessStatus.objects.create(
                student=other_holiday_student,
                month=closure_date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )
        else:
            MonthlyAccessStatus.objects.create(
                student=other_holiday_student,
                month=closure_date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )

        first_session = ClassSession.objects.create(
            section=self.section,
            date=closure_date,
            start_time=time(8, 0),
            end_time=time(9, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        second_session = ClassSession.objects.create(
            section=self.other_section,
            date=closure_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=first_session, student=self.active_student)
        Booking.objects.create_booking(session=second_session, student=other_holiday_student)
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-create-holiday-closure'),
            {
                'date': closure_date.isoformat(),
                'reason': 'Feriado puente',
                'notes': 'Se cierra todo el dia',
                'section': '',
            },
            follow=True,
        )

        closure = HolidayClosure.objects.get(date=closure_date)
        first_session.refresh_from_db()
        second_session.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(closure.created_by, self.staff_user)
        self.assertEqual(first_session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(second_session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(first_session.holiday_closure, closure)
        self.assertEqual(second_session.holiday_closure, closure)
        self.assertEqual(RecoveryCredit.objects.filter(source=RecoveryCreditSource.HOLIDAY_CLOSURE).count(), 2)
        audit_log = AuditLog.objects.get(entity_type='HolidayClosure', entity_id=closure.pk)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.action, AuditAction.CREATE)
        self.assertEqual(audit_log.payload['updated_sessions'], 2)
        self.assertEqual(audit_log.payload['created_credits'], 2)
        self.assertContains(response, 'Sesiones cerradas: 2.')
        self.assertContains(response, 'Recuperaciones nuevas: 2.')
        self.assertContains(response, 'Resumen del cierre')
        self.assertContains(response, 'Feriado puente')

    def test_staff_can_reapply_holiday_closure_without_duplicate_recoveries(self):
        closure_date = self.today + timedelta(days=12)
        MonthlyAccessStatus.objects.get_or_create(
            student=self.active_student,
            month=normalize_month_start(closure_date),
            defaults={
                'status': MonthlyAccessStatusType.ACTIVE,
                'booking_enabled': True,
            },
        )
        holiday_session = ClassSession.objects.create(
            section=self.section,
            date=closure_date,
            start_time=time(8, 0),
            end_time=time(9, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        Booking.objects.create_booking(session=holiday_session, student=self.active_student)
        self.client.force_login(self.staff_user)

        first_response = self.client.post(
            reverse('admin-create-holiday-closure'),
            {
                'date': closure_date.isoformat(),
                'reason': 'Feriado local',
                'notes': 'Primer aviso',
                'section': '',
            },
            follow=True,
        )
        second_response = self.client.post(
            reverse('admin-create-holiday-closure'),
            {
                'date': closure_date.isoformat(),
                'reason': 'Feriado actualizado',
                'notes': 'Cambio operativo',
                'section': '',
            },
            follow=True,
        )

        closure = HolidayClosure.objects.get(date=closure_date)
        holiday_session.refresh_from_db()
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(HolidayClosure.objects.filter(date=closure_date).count(), 1)
        self.assertEqual(closure.reason, 'Feriado actualizado')
        self.assertEqual(closure.notes, 'Cambio operativo')
        self.assertEqual(holiday_session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(RecoveryCredit.objects.filter(source=RecoveryCreditSource.HOLIDAY_CLOSURE, origin_session=holiday_session).count(), 1)
        self.assertContains(second_response, 'Recuperaciones nuevas: 0.')
        self.assertContains(second_response, 'Recuperaciones ya existentes: 1.')

    def test_staff_agenda_surfaces_recovery_related_badges(self):
        makeup_student = User.objects.create_user(
            email='agenda-makeup@example.com',
            password='StudentPass2026!',
            first_name='Dorothy',
            last_name='Vaughan',
            primary_section=self.section,
            must_change_password=False,
        )
        MonthlyAccessStatus.objects.create(
            student=makeup_student,
            month=normalize_month_start(self.upcoming_session.date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=makeup_student,
            section=self.section,
            granted_by=self.staff_user,
            reference_date=self.upcoming_session.date,
        )
        Booking.objects.create_booking(
            session=self.upcoming_session,
            student=makeup_student,
            used_recovery_credit=recovery_credit,
        )
        RecoveryCredit.objects.create(
            student=self.active_student,
            section=self.section,
            source=RecoveryCreditSource.HOLIDAY_CLOSURE,
            status=RecoveryCreditStatus.AVAILABLE,
            origin_session=self.upcoming_session,
            expires_at=self.today + timedelta(days=20),
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse('admin-class-agenda'),
            {
                'date': self.today.isoformat(),
                'section': self.section.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 con recuperación')
        self.assertContains(response, '1 recuperaciones generadas')

    def test_staff_session_detail_surfaces_holiday_closure_impact(self):
        closure_date = self.today + timedelta(days=9)
        holiday_session = ClassSession.objects.create(
            section=self.section,
            date=closure_date,
            start_time=time(13, 0),
            end_time=time(14, 0),
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )
        MonthlyAccessStatus.objects.get_or_create(
            student=self.active_student,
            month=normalize_month_start(closure_date),
            defaults={
                'status': MonthlyAccessStatusType.ACTIVE,
                'booking_enabled': True,
            },
        )
        Booking.objects.create_booking(session=holiday_session, student=self.active_student)
        closure = HolidayClosure.objects.create(date=closure_date, reason='Feriado local', created_by=self.staff_user)
        closure.apply()
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin-class-session-detail', args=[holiday_session.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Impacto del cierre')
        self.assertContains(response, '1 reserva activa')
        self.assertContains(response, 'Cierre del día')
