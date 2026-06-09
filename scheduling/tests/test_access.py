from ._shared import *

class MonthlyAccessStatusModelTests(TestCase):
    def create_access(self, **overrides):
        student = overrides.pop('student', None) or User.objects.create_user(
            email=f"student-{timezone.now().timestamp()}@example.com",
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
        )
        defaults = {
            'student': student,
            'month': date(2026, 4, 1),
        }
        defaults.update(overrides)
        return MonthlyAccessStatus.objects.create(**defaults)

    def assert_status_transition_error(self, access, target_status):
        access.status = target_status

        with self.assertRaises(ValidationError) as exc:
            access.full_clean()

        self.assertIn('status', exc.exception.message_dict)
        self.assertIn('Invalid monthly access transition', exc.exception.message_dict['status'][0])

    def test_activate_by_payment_enables_operational_booking(self):
        student = User.objects.create_user(
            email='student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
        )
        admin_user = User.objects.create_user(
            email='admin@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            is_staff=True,
        )
        access = MonthlyAccessStatus.objects.create(
            student=student,
            month=date(2026, 4, 17),
        )

        access.activate_by_payment(actor=admin_user)

        access.refresh_from_db()
        self.assertEqual(access.month, date(2026, 4, 1))
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertEqual(access.activated_by, admin_user)
        self.assertIsNotNone(access.activated_at)
        self.assertIsNone(access.deactivated_at)

    def test_pending_payment_exposes_domain_allowed_transitions(self):
        access = self.create_access()

        self.assertEqual(
            access.available_status_transitions(),
            {
                MonthlyAccessStatusType.ACTIVE,
                MonthlyAccessStatusType.SUSPENDED,
            },
        )

    def test_mark_pending_payment_disables_operational_booking(self):
        admin_user = User.objects.create_user(
            email='pending-admin@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            is_staff=True,
        )
        access = self.create_access()
        access.activate_by_payment(actor=admin_user)

        access.mark_pending_payment()

        access.refresh_from_db()
        self.assertEqual(access.status, MonthlyAccessStatusType.PENDING_PAYMENT)
        self.assertFalse(access.booking_enabled)
        self.assertIsNone(access.activated_at)
        self.assertIsNone(access.deactivated_at)
        self.assertIsNone(access.activated_by)

    def test_suspended_access_cannot_transition_back_to_pending_payment(self):
        access = self.create_access(status=MonthlyAccessStatusType.SUSPENDED, booking_enabled=False)

        self.assert_status_transition_error(access, MonthlyAccessStatusType.PENDING_PAYMENT)

    def test_domain_transition_matrix_is_explicit_and_stable(self):
        self.assertEqual(
            MonthlyAccessStatus.STATUS_TRANSITIONS,
            {
                MonthlyAccessStatusType.PENDING_PAYMENT: frozenset({
                    MonthlyAccessStatusType.ACTIVE,
                    MonthlyAccessStatusType.SUSPENDED,
                }),
                MonthlyAccessStatusType.ACTIVE: frozenset({
                    MonthlyAccessStatusType.PENDING_PAYMENT,
                    MonthlyAccessStatusType.SUSPENDED,
                }),
                MonthlyAccessStatusType.SUSPENDED: frozenset({
                    MonthlyAccessStatusType.ACTIVE,
                }),
            },
        )

    def test_mark_pending_payment_rejects_invalid_suspended_transition(self):
        access = self.create_access(status=MonthlyAccessStatusType.SUSPENDED, booking_enabled=False)

        with self.assertRaises(ValidationError) as exc:
            access.mark_pending_payment()

        self.assertIn('status', exc.exception.message_dict)
        self.assertIn('Invalid monthly access transition', exc.exception.message_dict['status'][0])

    def test_transition_operations_persist_status_specific_fields(self):
        admin_user = User.objects.create_user(
            email='transition-admin@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            is_staff=True,
        )
        access = self.create_access()

        access.activate_by_payment(actor=admin_user)
        access.refresh_from_db()
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertEqual(access.activated_by, admin_user)
        self.assertIsNotNone(access.activated_at)
        self.assertIsNone(access.deactivated_at)

        activated_at = access.activated_at

        access.suspend_operational_access()
        access.refresh_from_db()
        self.assertEqual(access.status, MonthlyAccessStatusType.SUSPENDED)
        self.assertFalse(access.booking_enabled)
        self.assertEqual(access.activated_at, activated_at)
        self.assertEqual(access.activated_by, admin_user)
        self.assertIsNotNone(access.deactivated_at)

        access.activate_by_payment()
        access.refresh_from_db()
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertEqual(access.activated_by, admin_user)
        self.assertIsNotNone(access.activated_at)
        self.assertIsNone(access.deactivated_at)

        access.mark_pending_payment()
        access.refresh_from_db()
        self.assertEqual(access.status, MonthlyAccessStatusType.PENDING_PAYMENT)
        self.assertFalse(access.booking_enabled)
        self.assertIsNone(access.activated_at)
        self.assertIsNone(access.deactivated_at)
        self.assertIsNone(access.activated_by)

    def test_active_access_requires_booking_enabled(self):
        access = MonthlyAccessStatus(
            student=User.objects.create_user(
                email='flags@example.com',
                password='secret123',
                first_name='Katherine',
                last_name='Johnson',
            ),
            month=date(2026, 4, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=False,
        )

        with self.assertRaises(ValidationError) as exc:
            access.full_clean()

        self.assertIn('booking_enabled', exc.exception.message_dict)
        self.assertIn('Active monthly access must enable booking.', exc.exception.message_dict['booking_enabled'])

    def test_pending_payment_cannot_keep_transition_metadata(self):
        admin_user = User.objects.create_user(
            email='pending-metadata-admin@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            is_staff=True,
        )
        access = MonthlyAccessStatus(
            student=User.objects.create_user(
                email='pending-metadata@example.com',
                password='secret123',
                first_name='Dorothy',
                last_name='Vaughan',
            ),
            month=date(2026, 4, 1),
            status=MonthlyAccessStatusType.PENDING_PAYMENT,
            booking_enabled=False,
            activated_at=timezone.now(),
            deactivated_at=timezone.now(),
            activated_by=admin_user,
        )

        with self.assertRaises(ValidationError) as exc:
            access.full_clean()

        self.assertIn('activated_at', exc.exception.message_dict)
        self.assertIn('deactivated_at', exc.exception.message_dict)
        self.assertIn('activated_by', exc.exception.message_dict)

class SchedulingUseCaseTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.today = timezone.localdate()
        self.staff_user = User.objects.create_user(
            email='usecase-staff@example.com',
            password='StaffPass2026!',
            first_name='Grace',
            last_name='Hopper',
            is_staff=True,
        )
        self.student = User.objects.create_user(
            email='usecase-student@example.com',
            password='StudentPass2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )

    def test_activate_student_monthly_access_creates_and_activates_missing_status(self):
        result = activate_student_monthly_access(student=self.student, actor=self.staff_user, record_audit=True)

        self.assertTrue(result.created)
        self.assertTrue(result.changed)
        self.assertEqual(result.access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(result.access.booking_enabled)
        self.assertEqual(result.access.activated_by, self.staff_user)
        audit_log = AuditLog.objects.get(entity_type='MonthlyAccessStatus', entity_id=result.access.pk)
        self.assertEqual(audit_log.actor, self.staff_user)

    def test_suspend_student_monthly_access_suspends_pending_status(self):
        access = MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.today,
            status=MonthlyAccessStatusType.PENDING_PAYMENT,
            booking_enabled=False,
        )

        result = suspend_student_monthly_access(student=self.student, actor=self.staff_user, month=self.today, record_audit=True)

        access.refresh_from_db()
        self.assertFalse(result.created)
        self.assertTrue(result.changed)
        self.assertEqual(result.access.pk, access.pk)
        self.assertEqual(access.status, MonthlyAccessStatusType.SUSPENDED)
        self.assertFalse(access.booking_enabled)
        self.assertIsNotNone(access.deactivated_at)
        audit_log = AuditLog.objects.get(entity_type='MonthlyAccessStatus', entity_id=access.pk)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['status'], MonthlyAccessStatusType.SUSPENDED)

    def test_toggle_student_monthly_access_wraps_explicit_transitions(self):
        result = toggle_student_monthly_access(student=self.student, actor=self.staff_user, record_audit=True)

        self.assertTrue(result.activated)
        self.assertEqual(result.access.status, MonthlyAccessStatusType.ACTIVE)

    def test_grant_manual_recovery_credit_records_audit_without_duplicating_rules(self):
        credit = grant_manual_recovery_credit(
            student=self.student,
            section=self.section,
            granted_by=self.staff_user,
            notes='Cortesia operativa',
            record_audit=True,
        )

        self.assertEqual(credit.source, RecoveryCreditSource.MANUAL)
        self.assertEqual(credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertEqual(credit.granted_by, self.staff_user)
        audit_log = AuditLog.objects.get(entity_type='RecoveryCredit', entity_id=credit.pk, action=AuditAction.CREDIT)
        self.assertEqual(audit_log.payload['notes'], 'Cortesia operativa')

    def test_expire_recovery_credit_persists_transition_and_audit(self):
        credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today + timedelta(days=7),
        )

        result = expire_recovery_credit(credit=credit, actor=self.staff_user, on_date=self.today, record_audit=True)

        self.assertTrue(result.changed)
        self.assertEqual(credit.status, RecoveryCreditStatus.EXPIRED)
        self.assertEqual(credit.expires_at, self.today)
        audit_log = AuditLog.objects.get(entity_type='RecoveryCredit', entity_id=credit.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['reason'], 'manual')

    def test_expire_overdue_recovery_credits_reuses_single_credit_use_case_and_audit(self):
        overdue_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today - timedelta(days=2),
        )
        not_due_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=self.today + timedelta(days=5),
        )
        used_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.USED,
            expires_at=self.today - timedelta(days=1),
            used_at=timezone.now(),
        )

        result = expire_overdue_recovery_credits_use_case(
            credits=RecoveryCredit.objects.filter(pk__in=[overdue_credit.pk, not_due_credit.pk, used_credit.pk]).order_by('pk'),
            actor=self.staff_user,
            on_date=self.today,
            record_audit=True,
        )

        overdue_credit.refresh_from_db()
        not_due_credit.refresh_from_db()
        used_credit.refresh_from_db()
        self.assertEqual(result.expired_count, 1)
        self.assertEqual(result.skipped_count, 2)
        self.assertEqual(overdue_credit.status, RecoveryCreditStatus.EXPIRED)
        self.assertEqual(overdue_credit.expires_at, self.today - timedelta(days=2))
        self.assertEqual(not_due_credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertEqual(used_credit.status, RecoveryCreditStatus.USED)
        audit_log = AuditLog.objects.get(entity_type='RecoveryCredit', entity_id=overdue_credit.pk, action=AuditAction.STATUS_CHANGE)
        self.assertEqual(audit_log.actor, self.staff_user)
        self.assertEqual(audit_log.payload['reason'], 'overdue')
        self.assertEqual(
            AuditLog.objects.filter(entity_type='RecoveryCredit', action=AuditAction.STATUS_CHANGE).count(),
            1,
        )

    def test_apply_holiday_closure_reuses_existing_record_and_applies_domain(self):
        session = ClassSession.objects.create(
            section=self.section,
            date=self.today + timedelta(days=2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=5,
            status=SessionStatus.SCHEDULED,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        Booking.objects.create_booking(session=session, student=self.student)

        application = apply_holiday_closure(
            closure_date=session.date,
            reason='Feriado puente',
            notes='Se cierra todo el dia',
            actor=self.staff_user,
            record_audit=True,
        )

        session.refresh_from_db()
        self.assertTrue(application.created)
        self.assertEqual(session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(application.result['updated_sessions'], 1)
        self.assertEqual(application.result['created_credits'], 1)
        audit_log = AuditLog.objects.get(entity_type='HolidayClosure', entity_id=application.closure.pk)
        self.assertEqual(audit_log.actor, self.staff_user)

class RecoveryCreditModelTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')

    def create_credit(self, **overrides):
        student = overrides.pop('student', None) or User.objects.create_user(
            email=f'student-{timezone.now().timestamp()}@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
        )
        defaults = {
            'student': student,
            'section': self.section,
            'source': RecoveryCreditSource.MANUAL,
            'status': RecoveryCreditStatus.AVAILABLE,
            'expires_at': timezone.localdate() + timedelta(days=30),
        }
        defaults.update(overrides)
        return RecoveryCredit.objects.create(**defaults)

    def assert_status_transition_error(self, credit, target_status):
        credit.status = target_status

        with self.assertRaises(ValidationError) as exc:
            credit.full_clean()

        self.assertIn('status', exc.exception.message_dict)
        self.assertIn('Invalid recovery credit transition', exc.exception.message_dict['status'][0])

    def test_set_expiration_date_adds_three_months(self):
        student = User.objects.create_user(
            email='student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
        )
        recovery_credit = RecoveryCredit(
            student=student,
            section=self.section,
            source=RecoveryCreditSource.MANUAL,
            expires_at=date(2026, 1, 1),
        )

        expires_at = recovery_credit.set_expiration_date(reference_date=date(2026, 1, 31))

        self.assertEqual(expires_at, date(2026, 4, 30))

    def test_expire_if_needed_marks_available_credit_as_expired(self):
        recovery_credit = self.create_credit(expires_at=timezone.localdate() - timedelta(days=1))

        changed = recovery_credit.expire_if_needed()

        self.assertTrue(changed)
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.EXPIRED)

    def test_available_exposes_all_domain_allowed_transitions(self):
        recovery_credit = self.create_credit()

        self.assertEqual(
            recovery_credit.available_status_transitions(),
            {
                RecoveryCreditStatus.USED,
                RecoveryCreditStatus.EXPIRED,
                RecoveryCreditStatus.REVOKED,
            },
        )

    def test_used_credit_cannot_transition_to_expired(self):
        recovery_credit = self.create_credit(status=RecoveryCreditStatus.USED, used_at=timezone.now())

        self.assert_status_transition_error(recovery_credit, RecoveryCreditStatus.EXPIRED)

    def test_expired_credit_cannot_transition_to_used(self):
        recovery_credit = self.create_credit(status=RecoveryCreditStatus.EXPIRED)
        recovery_credit.used_at = timezone.now()

        self.assert_status_transition_error(recovery_credit, RecoveryCreditStatus.USED)

    def test_used_credit_requires_usage_timestamp(self):
        recovery_credit = self.create_credit()
        recovery_credit.status = RecoveryCreditStatus.USED
        recovery_credit.used_at = None

        with self.assertRaises(ValidationError) as exc:
            recovery_credit.full_clean()

        self.assertIn('used_at', exc.exception.message_dict)
        self.assertIn('Used recovery credits must keep the usage timestamp.', exc.exception.message_dict['used_at'])

class HolidayClosureProcessingTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.student = User.objects.create_user(
            email='holiday-student@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.other_student = User.objects.create_user(
            email='holiday-other@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.other_section,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=date(2026, 5, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        MonthlyAccessStatus.objects.create(
            student=self.other_student,
            month=date(2026, 5, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        self.session = ClassSession.objects.create(
            section=self.section,
            date=date(2026, 5, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=4,
            status=SessionStatus.SCHEDULED,
        )
        self.other_session = ClassSession.objects.create(
            section=self.other_section,
            date=date(2026, 5, 1),
            start_time=time(11, 0),
            end_time=time(12, 0),
            capacity=4,
            status=SessionStatus.SCHEDULED,
        )

    def test_holiday_closure_applies_to_entire_day(self):
        closure = HolidayClosure.objects.create(date=date(2026, 5, 1), reason='Dia del trabajador')

        result = closure.apply()

        self.session.refresh_from_db()
        self.other_session.refresh_from_db()
        self.assertEqual(result['updated_sessions'], 2)
        self.assertEqual(self.session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(self.other_session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(self.session.holiday_closure, closure)
        self.assertEqual(self.other_session.holiday_closure, closure)

    def test_holiday_closed_sessions_become_non_bookable(self):
        closure = HolidayClosure.objects.create(date=date(2026, 5, 1), reason='Dia del trabajador')
        closure.apply()

        with self.assertRaisesMessage(ValidationError, 'cannot be booked'):
            Booking.objects.create_booking(session=self.session, student=self.student)

    def test_holiday_closure_generates_recovery_credits_for_affected_bookings(self):
        Booking.objects.create_booking(session=self.session, student=self.student)
        Booking.objects.create_booking(session=self.other_session, student=self.other_student)
        closure = HolidayClosure.objects.create(date=date(2026, 5, 1), reason='Dia del trabajador')

        result = closure.apply()

        self.assertEqual(result['created_credits'], 2)
        credits = RecoveryCredit.objects.filter(source=RecoveryCreditSource.HOLIDAY_CLOSURE).order_by('student__email')
        self.assertEqual(credits.count(), 2)
        self.assertEqual(credits[0].section_id, self.other_session.section_id)
        self.assertEqual(credits[0].origin_session_id, self.other_session.id)
        self.assertEqual(credits[1].section_id, self.session.section_id)
        self.assertEqual(credits[1].origin_session_id, self.session.id)
        self.assertTrue(HolidayClosure.objects.get(pk=closure.pk).recovery_credits_processed)

    def test_holiday_closure_reprocessing_does_not_duplicate_recovery_credits(self):
        Booking.objects.create_booking(session=self.session, student=self.student)
        closure = HolidayClosure.objects.create(date=date(2026, 5, 1), reason='Dia del trabajador')

        first_run = closure.apply()
        second_run = closure.apply()

        self.assertEqual(first_run['created_credits'], 1)
        self.assertEqual(second_run['created_credits'], 0)
        self.assertEqual(second_run['existing_credits'], 1)
        self.assertEqual(RecoveryCredit.objects.filter(source=RecoveryCreditSource.HOLIDAY_CLOSURE).count(), 1)

    def test_apply_holiday_closure_command_creates_and_processes_the_day(self):
        Booking.objects.create_booking(session=self.session, student=self.student)
        out = StringIO()

        call_command(
            'apply_holiday_closure',
            '2026-05-01',
            '--reason',
            'Dia del trabajador',
            stdout=out,
        )

        closure = HolidayClosure.objects.get(date=date(2026, 5, 1))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(closure.reason, 'Dia del trabajador')
        self.assertIn('1 recovery credits created', out.getvalue())

    def test_apply_holiday_closure_command_reuses_existing_record_without_overwriting_metadata(self):
        Booking.objects.create_booking(session=self.session, student=self.student)
        closure = HolidayClosure.objects.create(
            date=date(2026, 5, 1),
            reason='Dia del trabajador',
            notes='Mantener esta nota',
        )
        out = StringIO()

        call_command('apply_holiday_closure', '2026-05-01', stdout=out)

        closure.refresh_from_db()
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, SessionStatus.HOLIDAY_CLOSED)
        self.assertEqual(closure.reason, 'Dia del trabajador')
        self.assertEqual(closure.notes, 'Mantener esta nota')
        self.assertIn('Applied holiday closure for 2026-05-01', out.getvalue())
