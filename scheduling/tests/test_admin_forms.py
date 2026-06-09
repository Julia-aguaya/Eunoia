from ._shared import *

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
