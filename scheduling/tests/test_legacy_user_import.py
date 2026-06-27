import json

from scheduling.legacy_user_import import build_legacy_temporary_password

from ._shared import *


class LegacyUsersJsonImportCommandTests(TestCase):
    @override_settings(SECRET_KEY='legacy-import-secret')
    def test_command_imports_users_and_activates_paid_students(self):
        payload = [
            {
                '_id': {'$oid': 'legacy-admin-1'},
                'nombre': 'Ornella',
                'apellido': 'Eunoia',
                'email': 'admin@example.com',
                'celular': '3411111111',
                'diasSemanales': 1,
                'password': '$2b$10$legacy-admin-hash',
                'pago': False,
                'rol': 'admin',
                'fechaRegistro': {'$date': '2025-05-23T20:51:24.471Z'},
            },
            {
                '_id': {'$oid': 'legacy-student-1'},
                'nombre': 'Luciana',
                'apellido': 'Castellani',
                'email': 'student@example.com',
                'celular': '3412222222',
                'diasSemanales': 2,
                'password': '$2b$10$legacy-student-hash',
                'pago': True,
                'rol': 'usuario',
                'fechaRegistro': {'$date': '2025-05-29T20:02:39.052Z'},
                'fechaPago': {'$date': '2026-06-10T23:38:34.529Z'},
                'resetPasswordToken': 'token-present',
            },
        ]

        with tempfile.NamedTemporaryFile('w', suffix='.json', encoding='utf-8', delete=False) as handle:
            json.dump(payload, handle)
            json_path = Path(handle.name)

        out = StringIO()
        call_command('import_legacy_users_json', str(json_path), stdout=out)

        admin_user = User.objects.get(email='admin@example.com')
        student_user = User.objects.get(email='student@example.com')

        self.assertEqual(admin_user.role, UserRole.ADMIN)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.must_change_password)

        self.assertEqual(student_user.role, UserRole.STUDENT)
        self.assertTrue(student_user.must_change_password)
        self.assertTrue(student_user.check_password(build_legacy_temporary_password(mock.Mock(
            legacy_id='legacy-student-1',
            email='student@example.com',
        ))))
        self.assertIn('legacy_user_id=legacy-student-1', student_user.notes)
        self.assertIn('legacy_reset_token_present=true', student_user.notes)
        self.assertFalse(student_user.password.startswith('$2b$'))

        access = student_user.monthly_access_statuses.get(month=date(2026, 6, 1))
        self.assertEqual(access.status, MonthlyAccessStatusType.ACTIVE)
        self.assertTrue(access.booking_enabled)
        self.assertIn('2 created', out.getvalue())
        self.assertIn('2 temporary passwords assigned', out.getvalue())

    @override_settings(SECRET_KEY='legacy-import-secret')
    def test_command_is_idempotent_without_resetting_existing_passwords(self):
        payload = [
            {
                '_id': {'$oid': 'legacy-student-2'},
                'nombre': 'Ada',
                'apellido': 'Lovelace',
                'email': 'ada@example.com',
                'celular': '3413333333',
                'diasSemanales': 3,
                'password': '$2b$10$legacy-hash',
                'pago': True,
                'rol': 'usuario',
                'fechaRegistro': {'$date': '2025-05-29T20:02:39.052Z'},
                'fechaPago': {'$date': '2026-06-10T23:38:34.529Z'},
            },
        ]

        with tempfile.NamedTemporaryFile('w', suffix='.json', encoding='utf-8', delete=False) as handle:
            json.dump(payload, handle)
            json_path = Path(handle.name)

        call_command('import_legacy_users_json', str(json_path))

        user = User.objects.get(email='ada@example.com')
        initial_hash = user.password

        call_command('import_legacy_users_json', str(json_path))

        user.refresh_from_db()
        self.assertEqual(User.objects.filter(email='ada@example.com').count(), 1)
        self.assertEqual(user.password, initial_hash)
        self.assertEqual(user.monthly_access_statuses.filter(month=date(2026, 6, 1)).count(), 1)

    def test_command_rejects_paid_users_without_payment_date(self):
        payload = [
            {
                '_id': {'$oid': 'legacy-student-3'},
                'nombre': 'Grace',
                'apellido': 'Hopper',
                'email': 'grace@example.com',
                'celular': '3414444444',
                'diasSemanales': 2,
                'password': '$2b$10$legacy-hash',
                'pago': True,
                'rol': 'usuario',
                'fechaRegistro': {'$date': '2025-05-29T20:02:39.052Z'},
            },
        ]

        with tempfile.NamedTemporaryFile('w', suffix='.json', encoding='utf-8', delete=False) as handle:
            json.dump(payload, handle)
            json_path = Path(handle.name)

        with self.assertRaises(CommandError) as raised:
            call_command('import_legacy_users_json', str(json_path))

        self.assertIn('pago=true requires fechaPago', str(raised.exception))
