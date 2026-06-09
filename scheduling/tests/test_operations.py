from ._shared import *

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
