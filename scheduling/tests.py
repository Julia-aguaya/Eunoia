from datetime import date, time, timedelta
from io import StringIO
from pathlib import Path
import tempfile

from config.settings import parse_database_url
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from .admin import (
    BookingAdminForm,
    HolidayClosureAdmin,
    MonthlyAccessStatusAdmin,
    RecoveryCreditAdmin,
    RecoveryCreditAdminForm,
    UserAdmin,
    UserChangeAdminForm,
    UserCreationAdminForm,
    activate_access_by_payment,
    expire_overdue_recovery_credits,
    apply_holiday_closures,
    reset_temporary_passwords,
    suspend_operational_access,
)
from .application.onboarding import create_student_onboarding, get_default_temporary_password, reset_temporary_password
from .application.recovery_credits import (
    expire_overdue_recovery_credits as expire_overdue_recovery_credits_use_case,
    expire_recovery_credit,
)
from .models import (
    AuditAction,
    AuditLog,
    Booking,
    BookingSource,
    BookingStatus,
    ClassSession,
    HolidayClosure,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    RecoveryCreditSource,
    RecoveryCreditStatus,
    Section,
    SessionStatus,
    User,
    WeeklyClassSlot,
    Weekday,
    normalize_month_start,
)
from .demo import DEMO_ADMIN_EMAIL, DEMO_STAFF_EMAIL, DEMO_STUDENT_PASSWORD
from .student_import import StudentImportValidationError, import_students_from_csv
from .use_cases import (
    activate_student_monthly_access,
    apply_holiday_closure,
    cancel_booking,
    create_booking,
    generate_class_sessions,
    grant_manual_recovery_credit,
    mark_booking_attended,
    mark_booking_no_show,
    suspend_student_monthly_access,
    toggle_student_monthly_access,
)


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


class DatabaseConfigTests(TestCase):
    def test_parse_database_url_supports_postgres_without_breaking_sqlite_default(self):
        config = parse_database_url('postgresql://eunoia:secret@db.example.com:5432/eunoia_prod')

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'eunoia_prod')
        self.assertEqual(config['USER'], 'eunoia')
        self.assertEqual(config['PASSWORD'], 'secret')
        self.assertEqual(config['HOST'], 'db.example.com')
        self.assertEqual(config['PORT'], '5432')

    def test_parse_database_url_keeps_sqlite_support(self):
        config = parse_database_url('sqlite:///tmp/eunoia.sqlite3')

        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(str(config['NAME']).replace('\\', '/'), '/tmp/eunoia.sqlite3')


class UserOnboardingTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')

    def test_set_temporary_password_hashes_value_and_flags_first_login_reset(self):
        user = User.objects.create_user(
            email='student-onboarding@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            must_change_password=False,
        )

        user.set_temporary_password('NuevaTemp2026!')
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.check_password('NuevaTemp2026!'))
        self.assertTrue(user.must_change_password)
        self.assertIsNotNone(user.temporary_password_set_at)

    def test_setting_permanent_password_clears_temporary_password_tracking(self):
        user = User.objects.create_user(
            email='student-permanent@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
        )

        user.set_initial_password('Definitiva2026!', require_password_change=False)
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.check_password('Definitiva2026!'))
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='OnboardingTemp2026!')
    def test_reset_temporary_password_use_case_uses_default_password_without_duplicating_model_rules(self):
        user = User.objects.create_user(
            email='student-reset@example.com',
            password='secret123',
            first_name='Hedy',
            last_name='Lamarr',
            must_change_password=False,
        )

        result = reset_temporary_password(users=User.objects.filter(pk=user.pk))

        user.refresh_from_db()
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(get_default_temporary_password(), 'OnboardingTemp2026!')
        self.assertTrue(user.check_password('OnboardingTemp2026!'))
        self.assertTrue(user.must_change_password)
        self.assertIsNotNone(user.temporary_password_set_at)

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='AltaManualTemp2026!')
    def test_create_student_onboarding_uses_default_password_and_model_flags(self):
        user = create_student_onboarding(
            email='alta-manual@example.com',
            first_name='Katherine',
            last_name='Johnson',
            primary_section=self.section,
            notes='Alta manual',
            must_change_password=False,
        )

        self.assertTrue(user.check_password('AltaManualTemp2026!'))
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)
        self.assertEqual(user.primary_section, self.section)


class UserAdminActionTests(TestCase):
    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='AdminActionTemp2026!')
    def test_reset_temporary_password_action_uses_onboarding_use_case(self):
        section = Section.objects.get(code='cadillac')
        acting_user = User.objects.create_user(
            email='staff-action@example.com',
            password='AdminSecret2026!',
            first_name='Staff',
            last_name='Action',
            role='admin',
            is_staff=True,
            primary_section=section,
        )
        target_user = User.objects.create_user(
            email='student-action@example.com',
            password='secret123',
            first_name='Student',
            last_name='Action',
            primary_section=section,
            must_change_password=False,
        )
        request = HttpRequest()
        request.user = acting_user
        admin_site = AdminSite()
        model_admin = UserAdmin(User, admin_site)
        messages = []
        model_admin.message_user = lambda _request, message: messages.append(message)

        reset_temporary_passwords(model_admin, request, User.objects.filter(pk=target_user.pk))

        target_user.refresh_from_db()
        self.assertTrue(target_user.check_password('AdminActionTemp2026!'))
        self.assertTrue(target_user.must_change_password)
        self.assertEqual(
            messages,
            ['Se resetearon 1 usuarias con la contrasena temporal configurada y cambio obligatorio en primer ingreso.'],
        )


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


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')

    def create_student(self, *, email, password, must_change_password):
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
            must_change_password=must_change_password,
        )
        if not must_change_password:
            user.temporary_password_set_at = None
            user.save(update_fields=['temporary_password_set_at', 'updated_at'])
        return user

    def test_login_correcto(self):
        user = self.create_student(
            email='login-ok@example.com',
            password='TempLogin2026!',
            must_change_password=False,
        )

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'TempLogin2026!'},
        )

        self.assertRedirects(response, reverse('dashboard'))
        follow_response = self.client.get(reverse('dashboard'))
        self.assertContains(follow_response, 'Portal Eunoia')

    def test_redireccion_obligatoria_por_must_change_password(self):
        user = self.create_student(
            email='must-change@example.com',
            password='TempForce2026!',
            must_change_password=True,
        )

        response = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'TempForce2026!'},
        )

        self.assertRedirects(response, reverse('change-password-required'))
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertRedirects(dashboard_response, reverse('change-password-required'))

    def test_cambio_de_password_exitoso(self):
        user = self.create_student(
            email='change-ok@example.com',
            password='TempChange2026!',
            must_change_password=True,
        )
        self.client.post(reverse('login'), {'email': user.email, 'password': 'TempChange2026!'})

        response = self.client.post(
            reverse('change-password-required'),
            {'new_password1': 'DefinitivaSegura2026!', 'new_password2': 'DefinitivaSegura2026!'},
        )

        self.assertRedirects(response, reverse('dashboard'))
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)
        self.assertTrue(user.check_password('DefinitivaSegura2026!'))
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, 'Tu estado del mes')

    def test_acceso_normal_cuando_ya_no_requiere_cambio(self):
        user = self.create_student(
            email='normal-access@example.com',
            password='DefinitivaNormal2026!',
            must_change_password=False,
        )

        self.client.post(reverse('login'), {'email': user.email, 'password': 'DefinitivaNormal2026!'})

        dashboard_response = self.client.get(reverse('dashboard'))
        change_password_response = self.client.get(reverse('change-password-required'))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, user.get_full_name())
        self.assertRedirects(change_password_response, reverse('dashboard'))

    def test_staff_login_redirects_to_admin_portal(self):
        staff_user = User.objects.create_user(
            email='staff-login@example.com',
            password='StaffPortal2026!',
            first_name='Grace',
            last_name='Hopper',
            role='admin',
            is_staff=True,
            must_change_password=False,
        )
        staff_user.temporary_password_set_at = None
        staff_user.save(update_fields=['temporary_password_set_at', 'updated_at'])

        response = self.client.post(
            reverse('login'),
            {'email': staff_user.email, 'password': 'StaffPortal2026!'},
        )

        self.assertRedirects(response, reverse('admin-student-list'))


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
        self.assertContains(response, 'Al dia')
        self.assertNotContains(response, 'Grace Hopper')

    def test_staff_list_links_to_student_detail(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin-student-list'), {'q': 'ada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin-student-detail', args=[self.active_student.pk]))

    def test_staff_can_view_student_detail_operational_snapshot(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin-student-detail', args=[self.active_student.pk]), {'q': 'ada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ficha operativa de alumna.')
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, self.active_student.email)
        self.assertContains(response, self.section.name)
        self.assertContains(response, 'Proximas reservas')
        self.assertContains(response, 'Recuperaciones')
        self.assertContains(response, 'Vencida')
        self.assertContains(response, 'Resumen reciente')
        self.assertContains(response, 'Volver al listado')
        self.assertContains(response, 'Auditoria reciente')

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
        self.assertContains(response, 'Cortesia operativa')
        self.assertContains(response, 'Staff otorgo una recuperacion manual para Ada Lovelace')

    def test_staff_manual_recovery_requires_valid_section(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('admin-grant-manual-recovery', args=[self.active_student.pk]),
            {'notes': 'Sin actividad'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Actividad de la recuperacion')
        self.assertContains(response, 'Este campo es obligatorio.')
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
        self.assertContains(response, 'Vencida')

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
        self.assertContains(response, 'Suspendido')
        self.assertContains(response, 'Staff suspendio el acceso mensual de Ada Lovelace')

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
        self.assertContains(response, 'Suspendido')

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
        self.assertContains(response, 'Agenda operativa cercana')
        self.assertContains(response, self.section.name)
        self.assertContains(response, self.upcoming_session.start_time.strftime('%H:%M'))
        self.assertNotContains(response, self.other_upcoming_session.start_time.strftime('%H:%M'))

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
        self.assertContains(response, 'Detalle operativo de clase.')
        self.assertContains(response, self.section.name)
        self.assertContains(response, self.upcoming_session.date.strftime('%d/%m/%Y'))
        self.assertContains(response, 'Ocupacion actual')
        self.assertContains(response, '2 / 6')
        self.assertContains(response, 'Alumnas anotadas')
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, 'Katherine Johnson')
        self.assertContains(response, 'Reserva por recuperacion manual')
        self.assertContains(response, 'Con recuperacion')
        self.assertContains(response, 'Reservas relevantes recientes')
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
        self.assertContains(response, 'Impacto del dia elegido')
        self.assertContains(response, 'Feriado puente')

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
        self.assertContains(response, '1 con recuperacion')
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
        self.assertContains(response, 'Cierre por feriado')


class StudentPortalViewTests(TestCase):
    def setUp(self):
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
        self.today = timezone.localdate()
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

    def test_dashboard_displays_operational_summary(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acceso operativo activo')
        self.assertContains(response, 'Tus proximas clases')
        self.assertContains(response, self.section.name)

    def test_agenda_only_shows_primary_section_sessions(self):
        response = self.client.get(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.section.name)
        self.assertContains(response, 'Reservar')
        self.assertNotContains(response, self.other_section.name)

    def test_my_bookings_shows_active_booking_and_recovery_credit(self):
        response = self.client.get(reverse('my-bookings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reserva activa')
        self.assertContains(response, 'Disponible')
        self.assertContains(response, 'Disponibles y vencidas')

    def test_agenda_blocks_actions_when_operational_access_is_not_available(self):
        access = self.student.get_monthly_access_for(self.today)
        access.mark_pending_payment()

        response = self.client.get(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mes pendiente de pago')
        self.assertContains(response, 'Acciones bloqueadas')
        self.assertContains(response, 'Bloqueo operativo activo')

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

        response = self.client.get(reverse('agenda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sin cupo')
        self.assertContains(response, 'Ya reservado')
        self.assertContains(response, 'Reserva confirmada')

    def test_dashboard_highlights_blocked_operational_state(self):
        access = self.student.get_monthly_access_for(self.today)
        access.suspend_operational_access()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acceso operativo suspendido')
        self.assertContains(response, 'Operacion bloqueada')
        self.assertContains(response, 'Ver agenda sin reservar')

    def test_my_bookings_explains_operational_blocking(self):
        access = self.student.get_monthly_access_for(self.today)
        access.mark_pending_payment()

        response = self.client.get(reverse('my-bookings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu acceso mensual esta bloqueado')
        self.assertContains(response, 'no podes Reservar ni Cancelar desde la web')


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
        self.assertContains(response, 'Reserva confirmada')
        my_bookings_response = self.client.get(reverse('my-bookings'))
        self.assertContains(my_bookings_response, 'Reserva activa')
        self.assertContains(my_bookings_response, session.section.name)

    def test_student_without_operational_access_sees_clear_error(self):
        session = self.create_session()
        access = self.student.get_monthly_access_for(session.date)
        access.suspend_operational_access()

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(session=session, student=self.student).exists())
        self.assertContains(response, 'Tu acceso operativo no permite reservar esta clase en este mes.')

    def test_student_cannot_book_session_from_another_activity(self):
        session = self.create_session(section=self.other_section)

        response = self.post_booking(session)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(session=session, student=self.student).exists())
        self.assertContains(response, 'Esta clase corresponde a otra actividad. Solo podes reservar dentro de tu actividad principal.')

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
        self.assertContains(response, 'Ya tenes una reserva activa para esta clase.')

    def test_student_can_cancel_future_booking_from_my_bookings(self):
        session = self.create_session(days=4)
        booking = Booking.objects.create_booking(session=session, student=self.student)

        response = self.post_cancellation(booking)

        booking.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertContains(response, 'Se genero una recuperacion disponible hasta el')
        self.assertContains(response, 'No tenes reservas activas futuras por ahora.')
        self.assertEqual(RecoveryCredit.objects.filter(student=self.student, status=RecoveryCreditStatus.AVAILABLE).count(), 1)

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, 'No tenes reservas activas futuras.')
        self.assertContains(dashboard_response, '1 vigentes')

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


class WebRecoveryFlowTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.today = timezone.localdate()
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

    def test_recovery_page_prioritizes_same_section_sessions(self):
        origin_session = self.create_session(days=2, start_hour=8)
        eligible_session = self.create_session(days=5, start_hour=10)
        self.create_session(section=self.other_section, days=4, start_hour=11)
        credit = self.create_available_credit(origin_session=origin_session)
        if normalize_month_start(eligible_session.date) != normalize_month_start(self.today):
            MonthlyAccessStatus.objects.create(
                student=self.student,
                month=eligible_session.date,
                status=MonthlyAccessStatusType.ACTIVE,
                booking_enabled=True,
            )

        response = self.client.get(reverse('use-recovery', args=[credit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clases futuras para Recuperacion')
        self.assertContains(response, eligible_session.section.name)
        self.assertContains(response, 'Compatible')
        self.assertContains(response, 'La recuperacion solo sirve para otra clase de la misma actividad, no para la sesion original.')
        self.assertNotContains(response, self.other_section.name)

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
        self.assertContains(dashboard_response, '1 ya aplicadas')

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


class GenerateClassSessionsCommandTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.section.default_capacity = 8
        self.section.save(update_fields=['default_capacity', 'updated_at'])
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=None,
            starts_on=date(2026, 4, 1),
            is_active=True,
        )

    def test_command_generates_sessions_and_skips_duplicates(self):
        existing_session = self.slot.build_session_for_date(date(2026, 4, 6))
        existing_session.save()
        out = StringIO()

        call_command('generate_class_sessions', '2026-04-01', '2026-04-14', stdout=out)

        self.assertEqual(ClassSession.objects.count(), 2)
        self.assertTrue(
            ClassSession.objects.filter(
                section=self.section,
                date=date(2026, 4, 13),
                start_time=time(9, 0),
            ).exists()
        )
        self.assertIn('Created 1 sessions', out.getvalue())
        self.assertIn('Skipped duplicates: 1', out.getvalue())

    def test_command_marks_holiday_closure_sessions(self):
        holiday = HolidayClosure.objects.create(date=date(2026, 4, 6), reason='Feriado')

        call_command('generate_class_sessions', '2026-04-06', '2026-04-06')

        session = ClassSession.objects.get()
        self.assertEqual(session.holiday_closure, holiday)
        self.assertEqual(session.status, SessionStatus.HOLIDAY_CLOSED)


class GenerateClassSessionsUseCaseTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.section.default_capacity = 8
        self.section.save(update_fields=['default_capacity', 'updated_at'])
        self.slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=None,
            starts_on=date(2026, 4, 1),
            is_active=True,
        )

    def test_use_case_generates_sessions_and_reports_duplicates(self):
        self.slot.build_session_for_date(date(2026, 4, 6)).save()

        result = generate_class_sessions(start_date=date(2026, 4, 1), end_date=date(2026, 4, 14))

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.skipped_duplicates, 1)
        self.assertEqual(result.inspected_matches, 2)
        self.assertTrue(
            ClassSession.objects.filter(
                section=self.section,
                date=date(2026, 4, 13),
                start_time=time(9, 0),
            ).exists()
        )

    def test_use_case_supports_dry_run_without_persisting(self):
        result = generate_class_sessions(
            start_date=date(2026, 4, 6),
            end_date=date(2026, 4, 6),
            dry_run=True,
        )

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.skipped_duplicates, 0)
        self.assertEqual(ClassSession.objects.count(), 0)


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

        with self.assertRaisesMessage(ValidationError, 'primary section'):
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


class BookingAdminFormTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
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
            start_time=time(11, 0),
            end_time=time(12, 0),
            capacity=2,
            status=SessionStatus.SCHEDULED,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=self.session.date,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
    def test_admin_form_routes_creation_through_booking_logic(self):
        form = BookingAdminForm(
            data={
                'session': self.session.pk,
                'student': self.student.pk,
                'status': BookingStatus.BOOKED,
                'source': 'manual',
                'cancellation_generates_recovery': False,
                'notes': 'Admin booking',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        booking = form.save()

        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertEqual(booking.source, 'manual')

    def test_admin_form_rejects_non_booked_creation_status(self):
        form = BookingAdminForm(
            data={
                'session': self.session.pk,
                'student': self.student.pk,
                'status': BookingStatus.CANCELLED,
                'source': 'manual',
                'cancellation_generates_recovery': False,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('New bookings must be created as booked reservations.', form.non_field_errors())


class UserAdminFormTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='Stage5Temp2026!')
    def test_creation_form_uses_configured_default_temporary_password(self):
        form = UserCreationAdminForm(
            data={
                'email': 'new-student@example.com',
                'first_name': 'Ada',
                'last_name': 'Lovelace',
                'role': 'student',
                'primary_section': self.section.pk,
                'phone': '1234',
                'notes': 'Alta manual',
                'must_change_password': 'on',
                'is_active': 'on',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(user.check_password('Stage5Temp2026!'))
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.primary_section, self.section)
        self.assertIsNotNone(user.temporary_password_set_at)

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='Stage5Temp2026!')
    def test_creation_form_keeps_model_as_source_of_truth_for_password_flags(self):
        form = UserCreationAdminForm(
            data={
                'email': 'manual-no-flag@example.com',
                'first_name': 'Dorothy',
                'last_name': 'Vaughan',
                'role': 'student',
                'primary_section': self.section.pk,
                'phone': '555-0101',
                'notes': 'Alta manual sin forzar cambio',
                'is_active': 'on',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(user.check_password('Stage5Temp2026!'))
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)

    def test_change_form_allows_resetting_temporary_password(self):
        user = User.objects.create_user(
            email='existing-student@example.com',
            password='secret123',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
            must_change_password=False,
        )
        form = UserChangeAdminForm(
            data={
                'email': user.email,
                'password': user.password,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'primary_section': self.section.pk,
                'phone': user.phone,
                'notes': user.notes,
                'temporary_password': 'ResetTemp2026!',
                'must_change_password': '',
                'is_active': 'on',
            },
            instance=user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        updated_user = form.save()

        updated_user.refresh_from_db()
        self.assertTrue(updated_user.check_password('ResetTemp2026!'))
        self.assertTrue(updated_user.must_change_password)
        self.assertIsNotNone(updated_user.temporary_password_set_at)


class TemporaryPasswordCommandTests(TestCase):
    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='CommandTemp2026!')
    def test_command_updates_explicit_users_with_default_password(self):
        first_user = User.objects.create_user(
            email='first@example.com',
            password='secret123',
            first_name='First',
            last_name='Student',
        )
        second_user = User.objects.create_user(
            email='second@example.com',
            password='secret123',
            first_name='Second',
            last_name='Student',
        )
        out = StringIO()

        call_command('set_temporary_password', 'first@example.com', 'second@example.com', stdout=out)

        first_user.refresh_from_db()
        second_user.refresh_from_db()
        self.assertTrue(first_user.check_password('CommandTemp2026!'))
        self.assertTrue(second_user.check_password('CommandTemp2026!'))
        self.assertTrue(first_user.must_change_password)
        self.assertTrue(second_user.must_change_password)
        self.assertIn('Temporary password assigned to 2 users', out.getvalue())

    def test_command_can_target_all_students(self):
        student = User.objects.create_user(
            email='student-all@example.com',
            password='secret123',
            first_name='Ada',
            last_name='Lovelace',
            role='student',
        )
        admin_user = User.objects.create_user(
            email='admin-all@example.com',
            password='secret123',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True,
        )

        call_command('set_temporary_password', '--all-students', '--password', 'BulkTemp2026!')

        student.refresh_from_db()
        admin_user.refresh_from_db()
        self.assertTrue(student.check_password('BulkTemp2026!'))
        self.assertFalse(admin_user.check_password('BulkTemp2026!'))


class BootstrapEunoiaCommandTests(TestCase):
    def test_command_creates_admin_and_restores_base_sections(self):
        Section.objects.all().delete()
        out = StringIO()

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            'ops@example.com',
            '--admin-password',
            'BootstrapAdmin2026!',
            '--admin-first-name',
            'Ops',
            '--admin-last-name',
            'Lead',
            stdout=out,
        )

        admin_user = User.objects.get(email='ops@example.com')
        self.assertEqual(Section.objects.count(), 3)
        self.assertEqual(admin_user.first_name, 'Ops')
        self.assertEqual(admin_user.last_name, 'Lead')
        self.assertEqual(admin_user.role, 'admin')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
        self.assertFalse(admin_user.must_change_password)
        self.assertTrue(admin_user.check_password('BootstrapAdmin2026!'))
        self.assertIn('Bootstrap ready', out.getvalue())

    def test_command_updates_existing_admin_without_resetting_password_by_default(self):
        admin_user = User.objects.create_user(
            email='ops-existing@example.com',
            password='OriginalAdmin2026!',
            first_name='Old',
            last_name='Name',
            role='student',
            is_staff=False,
            must_change_password=True,
        )

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            admin_user.email,
            '--admin-password',
            'NewAdmin2026!',
            '--admin-first-name',
            'New',
            '--admin-last-name',
            'Owner',
        )

        admin_user.refresh_from_db()
        self.assertEqual(admin_user.first_name, 'New')
        self.assertEqual(admin_user.last_name, 'Owner')
        self.assertEqual(admin_user.role, 'admin')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertFalse(admin_user.must_change_password)
        self.assertTrue(admin_user.check_password('OriginalAdmin2026!'))
        self.assertFalse(admin_user.check_password('NewAdmin2026!'))

    def test_command_can_reset_existing_admin_password(self):
        admin_user = User.objects.create_user(
            email='ops-reset@example.com',
            password='OriginalAdmin2026!',
            first_name='Ops',
            last_name='Reset',
            role='admin',
            is_staff=True,
            must_change_password=False,
        )

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            admin_user.email,
            '--admin-password',
            'ResetAdmin2026!',
            '--reset-password',
        )

        admin_user.refresh_from_db()
        self.assertTrue(admin_user.check_password('ResetAdmin2026!'))
        self.assertFalse(admin_user.must_change_password)

    def test_command_can_seed_demo_slots_and_generate_upcoming_sessions(self):
        out = StringIO()

        call_command(
            'bootstrap_eunoia',
            '--admin-email',
            'ops-demo@example.com',
            '--admin-password',
            'BootstrapAdmin2026!',
            '--with-demo-slots',
            '--generate-next-days',
            '14',
            stdout=out,
        )

        self.assertEqual(WeeklyClassSlot.objects.count(), 6)
        self.assertGreater(ClassSession.objects.count(), 0)
        self.assertIn('demo slots created: 6', out.getvalue())
        self.assertIn('sessions generated:', out.getvalue())


class EunoiaReadinessCommandTests(TestCase):
    def test_command_reports_ok_when_minimum_data_exists(self):
        section = Section.objects.get(code='cadillac')
        User.objects.create_user(
            email='ops-ready@example.com',
            password='ReadyAdmin2026!',
            first_name='Ops',
            last_name='Ready',
            role='admin',
            is_staff=True,
        )
        WeeklyClassSlot.objects.create(
            section=section,
            weekday=Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_active=True,
        )
        out = StringIO()

        call_command('check_eunoia_readiness', '--strict', stdout=out)

        self.assertIn('Readiness check: OK', out.getvalue())
        self.assertIn('weekly_slots_active=1', out.getvalue())

    def test_command_fails_in_strict_mode_without_schedule_data(self):
        User.objects.create_user(
            email='ops-missing@example.com',
            password='ReadyAdmin2026!',
            first_name='Ops',
            last_name='Missing',
            role='admin',
            is_staff=True,
        )

        with self.assertRaises(CommandError):
            call_command('check_eunoia_readiness', '--strict')


class DemoSeedCommandTests(TestCase):
    def test_demo_seed_command_creates_repeatable_demo_data(self):
        out = StringIO()

        call_command('seed_demo_eunoia', stdout=out)

        self.assertTrue(User.objects.get(email=DEMO_ADMIN_EMAIL).check_password('DemoAdmin2026!'))
        self.assertTrue(User.objects.get(email=DEMO_STAFF_EMAIL).check_password('DemoStaff2026!'))
        self.assertEqual(User.objects.filter(role='student', email__endswith='.demo@example.com').count(), 6)
        self.assertEqual(WeeklyClassSlot.objects.filter(is_active=True).count(), 6)
        self.assertGreater(ClassSession.objects.filter(status=SessionStatus.SCHEDULED).count(), 0)

        ada = User.objects.get(email='ada.demo@example.com')
        bea = User.objects.get(email='bea.demo@example.com')
        clara = User.objects.get(email='clara.demo@example.com')
        dora = User.objects.get(email='dora.demo@example.com')
        eva = User.objects.get(email='eva.demo@example.com')
        current_month = normalize_month_start(timezone.localdate())

        self.assertEqual(
            ada.monthly_access_statuses.get(month=current_month).status,
            MonthlyAccessStatusType.ACTIVE,
        )
        self.assertEqual(
            bea.monthly_access_statuses.get(month=current_month).status,
            MonthlyAccessStatusType.PENDING_PAYMENT,
        )
        self.assertEqual(
            clara.monthly_access_statuses.get(month=current_month).status,
            MonthlyAccessStatusType.SUSPENDED,
        )
        self.assertTrue(
            Booking.objects.filter(student=ada, status=BookingStatus.BOOKED).exists()
        )
        self.assertTrue(
            Booking.objects.filter(student=dora, status=BookingStatus.BOOKED, source='makeup').exists()
        )
        self.assertTrue(
            RecoveryCredit.objects.filter(student=eva, status=RecoveryCreditStatus.AVAILABLE).exists()
        )
        self.assertTrue(User.objects.get(email='sofia.demo@example.com').check_password(DEMO_STUDENT_PASSWORD))
        self.assertIn('Demo ready', out.getvalue())


class DemoSmokeCommandTests(TestCase):
    def test_demo_smoke_command_passes_against_seeded_data(self):
        call_command('seed_demo_eunoia')
        original_booking_count = Booking.objects.count()
        original_recovery_count = RecoveryCredit.objects.count()
        out = StringIO()

        call_command('smoke_test_eunoia_demo', stdout=out)

        self.assertIn('Demo smoke test: OK', out.getvalue())
        self.assertEqual(Booking.objects.count(), original_booking_count)
        self.assertEqual(RecoveryCredit.objects.count(), original_recovery_count)


class StudentCsvImportTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')

    def test_import_rejects_missing_required_columns(self):
        csv_content = StringIO(
            'email,first_name,last_name,role,is_active\n'
            'new-student@example.com,Ada,Lovelace,student,true\n'
        )

        with self.assertRaises(StudentImportValidationError) as raised:
            import_students_from_csv(csv_content)

        self.assertIn('Missing required CSV columns: primary_section.', str(raised.exception))

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='CsvTemp2026!')
    def test_import_creates_new_student_with_default_temporary_password(self):
        csv_content = StringIO(
            'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
            'new-student@example.com,Ada,Lovelace,cadillac,student,true,true,,1234,Alta inicial\n'
        )

        result = import_students_from_csv(csv_content)

        user = User.objects.get(email='new-student@example.com')
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 0)
        self.assertEqual(user.primary_section, self.section)
        self.assertTrue(user.check_password('CsvTemp2026!'))
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.phone, '1234')
        self.assertEqual(user.notes, 'Alta inicial')

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='CsvTemp2026!')
    def test_import_creates_new_student_with_onboarding_flags_when_password_change_is_disabled(self):
        csv_content = StringIO(
            'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
            'no-reset@example.com,Ada,Lovelace,cadillac,student,true,false,,1234,Alta sin reset\n'
        )

        result = import_students_from_csv(csv_content)

        user = User.objects.get(email='no-reset@example.com')
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 0)
        self.assertTrue(user.check_password('CsvTemp2026!'))
        self.assertFalse(user.must_change_password)
        self.assertIsNone(user.temporary_password_set_at)

    def test_import_updates_existing_user_without_resetting_password_when_column_is_blank(self):
        user = User.objects.create_user(
            email='existing-student@example.com',
            password='ExistingPass2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
            must_change_password=False,
            phone='1111',
        )
        original_password_hash = user.password

        csv_content = StringIO(
            'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
            'existing-student@example.com,Greta,Hopper,reformer_arriba,student,false,true,,2222,Actualizada por CSV\n'
        )

        result = import_students_from_csv(csv_content)

        user.refresh_from_db()
        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(user.first_name, 'Greta')
        self.assertEqual(user.primary_section, self.other_section)
        self.assertFalse(user.is_active)
        self.assertEqual(user.phone, '2222')
        self.assertEqual(user.notes, 'Actualizada por CSV')
        self.assertEqual(user.password, original_password_hash)
        self.assertTrue(user.check_password('ExistingPass2026!'))
        self.assertFalse(user.must_change_password)

    def test_import_rejects_invalid_email_section_role_and_boolean(self):
        csv_content = StringIO(
            'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
            'bad-email,Ada,Lovelace,mat,manager,maybe,true,,1234,Alta inicial\n'
        )

        with self.assertRaises(StudentImportValidationError) as raised:
            import_students_from_csv(csv_content)

        message = str(raised.exception)
        self.assertIn('invalid email', message)
        self.assertIn('unknown primary_section', message)
        self.assertIn('invalid role', message)
        self.assertIn('Invalid boolean value', message)

    @override_settings(EUNOIA_DEFAULT_TEMPORARY_PASSWORD='CsvTemp2026!')
    def test_management_command_imports_csv_file(self):
        csv_body = (
            'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
            'command-student@example.com,Ada,Lovelace,cadillac,student,true,true,,1234,Importada por comando\n'
        )
        out = StringIO()

        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='', suffix='.csv', delete=False) as temp_file:
            temp_file.write(csv_body)
            temp_path = Path(temp_file.name)

        try:
            call_command('import_students_csv', str(temp_path), stdout=out)
        finally:
            temp_path.unlink(missing_ok=True)

        user = User.objects.get(email='command-student@example.com')
        self.assertTrue(user.check_password('CsvTemp2026!'))
        self.assertIn('1 users created, 0 users updated', out.getvalue())


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

    def test_using_recovery_on_different_activity_is_rejected(self):
        start_at = timezone.now() + timedelta(days=5)
        session = self.create_session(section=self.other_section, start_at=start_at)
        self.grant_access(self.other_student, session.date)
        recovery_credit = RecoveryCredit.objects.grant_manual_credit(
            student=self.other_student,
            section=self.section,
            granted_by=self.admin_user,
            reference_date=timezone.localdate(),
        )

        with self.assertRaisesMessage(ValidationError, 'same section'):
            Booking.objects.create_booking(
                session=session,
                student=self.other_student,
                used_recovery_credit=recovery_credit,
            )

        recovery_credit.refresh_from_db()
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertIsNone(recovery_credit.used_at)

    def test_using_recovery_on_original_session_is_rejected(self):
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

        with self.assertRaisesMessage(ValidationError, 'another session in the same section'):
            Booking.objects.create_booking(
                session=session,
                student=self.student,
                used_recovery_credit=recovery_credit,
            )

        recovery_credit.refresh_from_db()
        self.assertEqual(recovery_credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertIsNone(recovery_credit.used_at)

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
