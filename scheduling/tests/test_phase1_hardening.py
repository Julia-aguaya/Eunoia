import subprocess
import sys
import threading
from io import StringIO
from pathlib import Path
from unittest import mock

from django.db import close_old_connections, connection
from django.test import SimpleTestCase, TransactionTestCase

from ._shared import *
from scheduling.admin import deactivate_students_globally
from scheduling import fixed_booking_history
from scheduling.use_cases import deactivate_student_globally as real_deactivate_student_globally


class LegacyRawSqlScriptTests(SimpleTestCase):
    def test_legacy_scripts_fail_closed_before_connecting_to_mysql(self):
        root = Path(__file__).resolve().parents[2]
        for script_name in (
            'run_cadillac_load.py',
            'run_reformer_arriba_load.py',
            'fix_reformer_arriba_viernes.py',
        ):
            self.assertFalse((root / script_name).exists(), f'{script_name} must stay removed')
            result = subprocess.run(
                [sys.executable, str(root / script_name)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn('No such file', result.stderr)


class StudentActivationHardeningTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')

    def _change_form_data(self, user, *, is_active):
        return {
            'email': user.email,
            'password': user.password,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'primary_section': self.section.pk,
            'phone': user.phone,
            'notes': user.notes,
            'must_change_password': '',
            'is_active': is_active,
        }

    def test_admin_form_cannot_directly_mutate_student_activation(self):
        student = User.objects.create_user(
            email='student@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section,
        )
        form = UserChangeAdminForm(data=self._change_form_data(student, is_active=''), instance=student)

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        student.refresh_from_db()
        self.assertTrue(student.is_active)

        user_admin = UserAdmin(User, AdminSite())
        self.assertIn('is_active', user_admin.get_readonly_fields(None, student))

    def test_global_admin_action_uses_canonical_student_deactivation(self):
        student = User.objects.create_user(
            email='action-student@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section,
        )
        modeladmin = mock.Mock()
        request = mock.Mock(user=None)

        with mock.patch('scheduling.admin.deactivate_student_globally', return_value=True) as deactivation:
            deactivate_students_globally(modeladmin, request, User.objects.filter(pk=student.pk))

        deactivation.assert_called_once_with(student=student, actor=None)

    def test_csv_deactivation_delegates_to_canonical_transition_before_save(self):
        student = User.objects.create_user(
            email='csv-student@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section,
        )
        csv_content = StringIO(
            'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
            'csv-student@example.com,Updated,Student,cadillac,student,false,,,,\n'
        )

        with mock.patch(
            'scheduling.student_import.deactivate_student_globally',
            wraps=real_deactivate_student_globally,
        ) as deactivation:
            import_students_from_csv(csv_content)

        deactivation.assert_called_once()
        student.refresh_from_db()
        self.assertFalse(student.is_active)
        self.assertEqual(student.first_name, 'Updated')

    def test_csv_blank_activation_does_not_implicitly_reactivate_student(self):
        student = User.objects.create_user(
            email='inactive-student@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section, is_active=False,
        )
        csv_content = StringIO(
            'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
            'inactive-student@example.com,Updated,Student,cadillac,student,,,,,\n'
        )

        import_students_from_csv(csv_content)

        student.refresh_from_db()
        self.assertFalse(student.is_active)

    def test_admin_user_remains_directly_editable(self):
        admin_user = User.objects.create_user(
            email='admin@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section, role='admin', is_staff=True,
        )
        form = UserChangeAdminForm(data=self._change_form_data(admin_user, is_active=''), instance=admin_user)

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        admin_user.refresh_from_db()
        self.assertFalse(admin_user.is_active)


class StudentDeactivationLockingTests(TransactionTestCase):
    """Verify row-lock serialization on databases that implement SELECT FOR UPDATE."""

    def setUp(self):
        if not connection.features.has_select_for_update:
            self.skipTest('This race test requires database row locking.')
        self.section, _ = Section.objects.get_or_create(code='cadillac', defaults={'name': 'Cadillac'})
        self.student = User.objects.create_user(
            email='locking-student@example.com', password='secret123', first_name='Ada', last_name='Lovelace',
            primary_section=self.section,
        )
        self.session = ClassSession.objects.create(
            section=self.section, date=timezone.localdate() + timedelta(days=1), start_time=time(9), end_time=time(10),
            capacity=4, status=SessionStatus.SCHEDULED,
        )
        MonthlyAccessStatus.objects.create(
            student=self.student,
            month=normalize_month_start(self.session.date),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )

    def _thread(self, target, errors):
        def run():
            close_old_connections()
            try:
                target()
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        thread = threading.Thread(target=run)
        thread.start()
        return thread

    def test_deactivation_serializes_against_booking_creation(self):
        entered_create = threading.Event()
        release_create = threading.Event()
        deactivation_started = threading.Event()
        errors = []
        original_create = Booking.objects.create_booking

        def pause_after_locks(*args, **kwargs):
            entered_create.set()
            self.assertTrue(release_create.wait(timeout=10))
            return original_create(*args, **kwargs)

        with mock.patch.object(Booking.objects, 'create_booking', side_effect=pause_after_locks):
            create_thread = self._thread(
                lambda: create_booking(session_id=self.session.pk, student=User.objects.get(pk=self.student.pk)),
                errors,
            )
            self.assertTrue(entered_create.wait(timeout=10))
            deactivate_thread = self._thread(
                lambda: (deactivation_started.set(), deactivate_student_globally(student=User.objects.get(pk=self.student.pk))),
                errors,
            )
            self.assertTrue(deactivation_started.wait(timeout=10))
            release_create.set()
            create_thread.join(timeout=15)
            deactivate_thread.join(timeout=15)

        self.assertFalse(create_thread.is_alive())
        self.assertFalse(deactivate_thread.is_alive())
        self.assertEqual(errors, [])
        self.student.refresh_from_db()
        booking = Booking.objects.get(session=self.session, student=self.student)
        self.assertFalse(self.student.is_active)
        self.assertEqual(booking.status, BookingStatus.CANCELLED)

    def test_deactivation_serializes_against_technical_booking_restore(self):
        slot = WeeklyClassSlot.objects.create(
            section=self.section, weekday=self.session.date.isoweekday(), start_time=self.session.start_time,
            end_time=self.session.end_time, is_active=True,
        )
        StudentMonthlyPlan.objects.create(
            student=self.student, month=normalize_month_start(self.session.date), section=self.section,
            is_active=True,
        ).assign_weekly_slots([slot])
        booking = Booking.objects.create_booking(session=self.session, student=self.student)
        Booking.objects.filter(pk=booking.pk).update(status=BookingStatus.CANCELLED, cancelled_at=timezone.now())
        entered_restore = threading.Event()
        release_restore = threading.Event()
        deactivation_started = threading.Event()
        errors = []
        original_restore = fixed_booking_history._restore_fixed_booking

        def pause_before_restore(historical_booking):
            entered_restore.set()
            self.assertTrue(release_restore.wait(timeout=10))
            return original_restore(historical_booking)

        with mock.patch.object(fixed_booking_history, '_restore_fixed_booking', side_effect=pause_before_restore):
            restore_thread = self._thread(
                lambda: fixed_booking_history.restore_recreatable_fixed_booking(
                    session=ClassSession.objects.get(pk=self.session.pk),
                    student=User.objects.get(pk=self.student.pk),
                    historical_bookings_by_session_id={},
                ),
                errors,
            )
            self.assertTrue(entered_restore.wait(timeout=10))
            deactivate_thread = self._thread(
                lambda: (deactivation_started.set(), deactivate_student_globally(student=User.objects.get(pk=self.student.pk))),
                errors,
            )
            self.assertTrue(deactivation_started.wait(timeout=10))
            release_restore.set()
            restore_thread.join(timeout=15)
            deactivate_thread.join(timeout=15)

        self.assertFalse(restore_thread.is_alive())
        self.assertFalse(deactivate_thread.is_alive())
        self.assertEqual(errors, [])
        self.student.refresh_from_db()
        booking.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertEqual(booking.status, BookingStatus.CANCELLED)
