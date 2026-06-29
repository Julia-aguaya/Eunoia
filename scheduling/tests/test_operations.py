from datetime import datetime
from typing import Any, cast

from ._shared import *

class DatabaseConfigTests(TestCase):
    def test_parse_database_url_supports_mysql_without_breaking_sqlite_default(self):
        config = parse_database_url('mysql://eunoia:secret@db.example.com:3306/eunoia_prod')

        self.assertEqual(config['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(config['NAME'], 'eunoia_prod')
        self.assertEqual(config['USER'], 'eunoia')
        self.assertEqual(config['PASSWORD'], 'secret')
        self.assertEqual(config['HOST'], 'db.example.com')
        self.assertEqual(config['PORT'], '3306')
        self.assertEqual(config['OPTIONS']['charset'], 'utf8mb4')
        self.assertEqual(config['CONN_MAX_AGE'], 60)
        self.assertTrue(config['CONN_HEALTH_CHECKS'])

    def test_parse_database_url_supports_common_mysql_query_options(self):
        config = parse_database_url(
            'mysql://eunoia:secret@db.example.com:3306/eunoia_prod?charset=utf8mb4&connect_timeout=5&conn_max_age=120&sql_mode=STRICT_TRANS_TABLES&ssl_ca=%2Ftmp%2Fca.pem'
        )
        options = cast(dict[str, Any], config['OPTIONS'])

        self.assertEqual(options.get('charset'), 'utf8mb4')
        self.assertEqual(options.get('connect_timeout'), 5)
        self.assertEqual(options.get('init_command'), "SET sql_mode='STRICT_TRANS_TABLES'")
        self.assertEqual(options.get('ssl', {}).get('ca'), '/tmp/ca.pem')
        self.assertEqual(config['CONN_MAX_AGE'], 120)

    def test_parse_database_url_supports_postgres_without_breaking_sqlite_default(self):
        config = parse_database_url('postgresql://eunoia:secret@db.example.com:5432/eunoia_prod')

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'eunoia_prod')
        self.assertEqual(config['USER'], 'eunoia')
        self.assertEqual(config['PASSWORD'], 'secret')
        self.assertEqual(config['HOST'], 'db.example.com')
        self.assertEqual(config['PORT'], '5432')
        self.assertEqual(config['CONN_MAX_AGE'], 60)
        self.assertTrue(config['CONN_HEALTH_CHECKS'])

    def test_parse_database_url_supports_common_postgres_query_options(self):
        config = parse_database_url(
            'postgresql://eunoia:secret@db.example.com:5432/eunoia_prod?sslmode=require&connect_timeout=5&conn_max_age=120'
        )

        self.assertEqual(config['OPTIONS']['sslmode'], 'require')
        self.assertEqual(config['OPTIONS']['connect_timeout'], 5)
        self.assertEqual(config['CONN_MAX_AGE'], 120)

    def test_parse_database_url_keeps_sqlite_support(self):
        config = parse_database_url('sqlite:///tmp/eunoia.sqlite3')

        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(str(config['NAME']).replace('\\', '/'), '/tmp/eunoia.sqlite3')

    def test_database_config_requires_explicit_database_in_production_without_sqlite_opt_in(self):
        with mock.patch.dict(
            'os.environ',
            {
                'DATABASE_URL': '',
                'DJANGO_DB_ENGINE': '',
                'DJANGO_USE_SQLITE': 'False',
                'DJANGO_DEBUG': 'False',
            },
            clear=False,
        ):
            with self.assertRaises(ImproperlyConfigured):
                database_config()

    def test_database_config_supports_explicit_mysql_engine_settings(self):
        with mock.patch.dict(
            'os.environ',
            {
                'DATABASE_URL': '',
                'DJANGO_DB_ENGINE': 'django.db.backends.mysql',
                'DJANGO_DB_NAME': 'eunoia_prod',
                'DJANGO_DB_USER': 'eunoia',
                'DJANGO_DB_PASSWORD': 'secret',
                'DJANGO_DB_HOST': 'db.example.com',
                'DJANGO_DB_PORT': '3306',
                'DJANGO_DB_CHARSET': 'utf8mb4',
                'DJANGO_DB_CONNECT_TIMEOUT': '7',
                'DJANGO_DB_SQL_MODE': 'STRICT_TRANS_TABLES',
            },
            clear=False,
        ):
            config = database_config()
        options = cast(dict[str, Any], config['OPTIONS'])

        self.assertEqual(config['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(config['NAME'], 'eunoia_prod')
        self.assertEqual(options.get('charset'), 'utf8mb4')
        self.assertEqual(options.get('connect_timeout'), 7)
        self.assertEqual(options.get('init_command'), "SET sql_mode='STRICT_TRANS_TABLES'")

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

    def test_use_case_auto_books_active_monthly_plan_slots_for_published_sessions(self):
        student = User.objects.create_user(
            email='auto-booked-student@example.com',
            password='StudentPlan2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=student,
            month=date(2026, 4, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=student,
            month=date(2026, 4, 1),
            section=self.section,
        )
        plan.assign_weekly_slots([self.slot])

        generate_class_sessions(start_date=date(2026, 4, 6), end_date=date(2026, 4, 6))

        session = ClassSession.objects.get(section=self.section, date=date(2026, 4, 6), start_time=time(9, 0))
        booking = Booking.objects.get(session=session, student=student)
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertEqual(booking.source, BookingSource.FIXED_SLOT)

    def test_use_case_does_not_duplicate_manual_booking_for_matching_plan_session(self):
        student = User.objects.create_user(
            email='manual-booking-student@example.com',
            password='StudentPlan2026!',
            first_name='Grace',
            last_name='Hopper',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=student,
            month=date(2026, 4, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        session = self.slot.build_session_for_date(date(2026, 4, 6))
        session.save()
        manual_booking = Booking.objects.create_booking(
            session=session,
            student=student,
            source=BookingSource.MANUAL,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=student,
            month=date(2026, 4, 1),
            section=self.section,
        )
        plan.assign_weekly_slots([self.slot])

        generate_class_sessions(start_date=date(2026, 4, 6), end_date=date(2026, 4, 6))

        bookings = Booking.objects.filter(session=session, student=student)
        self.assertEqual(bookings.count(), 1)
        self.assertEqual(bookings.get().pk, manual_booking.pk)
        self.assertEqual(bookings.get().source, BookingSource.MANUAL)

    def test_use_case_auto_books_matching_manual_published_session_without_slot_link(self):
        student = User.objects.create_user(
            email='manual-session-plan-student@example.com',
            password='StudentPlan2026!',
            first_name='Hedy',
            last_name='Lamarr',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=student,
            month=date(2026, 4, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=student,
            month=date(2026, 4, 1),
            section=self.section,
        )
        plan.assign_weekly_slots([self.slot])
        ClassSession.objects.create(
            section=self.section,
            date=date(2026, 4, 6),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=8,
            status=SessionStatus.SCHEDULED,
        )

        generate_class_sessions(start_date=date(2026, 4, 6), end_date=date(2026, 4, 6))

        session = ClassSession.objects.get(section=self.section, date=date(2026, 4, 6), start_time=time(9, 0))
        booking = Booking.objects.get(session=session, student=student)
        self.assertEqual(booking.status, BookingStatus.BOOKED)
        self.assertEqual(booking.source, BookingSource.FIXED_SLOT)

    def test_use_case_does_not_recreate_fixed_slot_booking_after_student_cancels(self):
        student = User.objects.create_user(
            email='cancelled-auto-booking-student@example.com',
            password='StudentPlan2026!',
            first_name='Katherine',
            last_name='Johnson',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=student,
            month=date(2026, 4, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=student,
            month=date(2026, 4, 1),
            section=self.section,
        )
        plan.assign_weekly_slots([self.slot])

        generate_class_sessions(start_date=date(2026, 4, 13), end_date=date(2026, 4, 13))

        session = ClassSession.objects.get(section=self.section, date=date(2026, 4, 13), start_time=time(9, 0))
        booking = Booking.objects.get(session=session, student=student)
        cancellation_time = timezone.make_aware(datetime(2026, 4, 10, 9, 0))

        cancel_booking(booking_id=booking.id, student=student, actor=student, when=cancellation_time)
        generate_class_sessions(start_date=date(2026, 4, 13), end_date=date(2026, 4, 13))

        self.assertEqual(Booking.objects.filter(session=session, student=student).count(), 1)
        self.assertFalse(Booking.objects.filter(session=session, student=student, status=BookingStatus.BOOKED).exists())
        self.assertTrue(Booking.objects.filter(session=session, student=student, status=BookingStatus.CANCELLED).exists())

    def test_use_case_auto_books_cross_month_grace_window_without_new_month_access(self):
        wednesday_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=None,
            starts_on=date(2026, 6, 1),
            is_active=True,
        )
        student = User.objects.create_user(
            email='cross-month-auto-booked-student@example.com',
            password='StudentPlan2026!',
            first_name='Dorothy',
            last_name='Vaughan',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=student,
            month=date(2026, 6, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        plan = StudentMonthlyPlan.objects.create(
            student=student,
            month=date(2026, 6, 1),
            section=self.section,
        )
        plan.assign_weekly_slots([self.slot, wednesday_slot])

        generate_class_sessions(start_date=date(2026, 6, 29), end_date=date(2026, 7, 1))

        monday_session = ClassSession.objects.get(section=self.section, date=date(2026, 6, 29), start_time=time(9, 0))
        wednesday_session = ClassSession.objects.get(section=self.section, date=date(2026, 7, 1), start_time=time(9, 0))
        self.assertTrue(Booking.objects.filter(session=monday_session, student=student, status=BookingStatus.BOOKED).exists())
        self.assertTrue(Booking.objects.filter(session=wednesday_session, student=student, status=BookingStatus.BOOKED).exists())

    def test_use_case_auto_books_active_monthly_plan_slots_for_multiple_sections_in_same_month(self):
        other_section = Section.objects.get(code='reformer_arriba')
        other_slot = WeeklyClassSlot.objects.create(
            section=other_section,
            weekday=Weekday.TUESDAY,
            start_time=time(11, 0),
            end_time=time(12, 0),
            is_active=True,
        )
        student = User.objects.create_user(
            email='multi-section-auto-booked-student@example.com',
            password='StudentPlan2026!',
            first_name='Dorothy',
            last_name='Vaughan',
            primary_section=self.section,
        )
        MonthlyAccessStatus.objects.create(
            student=student,
            month=date(2026, 4, 1),
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        StudentMonthlyPlan.objects.create(
            student=student,
            month=date(2026, 4, 1),
            section=self.section,
        ).assign_weekly_slots([self.slot])
        StudentMonthlyPlan.objects.create(
            student=student,
            month=date(2026, 4, 1),
            section=other_section,
        ).assign_weekly_slots([other_slot])

        generate_class_sessions(start_date=date(2026, 4, 6), end_date=date(2026, 4, 7))

        monday_session = ClassSession.objects.get(section=self.section, date=date(2026, 4, 6), start_time=time(9, 0))
        tuesday_session = ClassSession.objects.get(section=other_section, date=date(2026, 4, 7), start_time=time(11, 0))
        self.assertTrue(Booking.objects.filter(session=monday_session, student=student, status=BookingStatus.BOOKED).exists())
        self.assertTrue(Booking.objects.filter(session=tuesday_session, student=student, status=BookingStatus.BOOKED).exists())


class StudentMonthlyPlanModelTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.other_section = Section.objects.get(code='reformer_arriba')
        self.student = User.objects.create_user(
            email='monthly-plan-student@example.com',
            password='StudentPlan2026!',
            first_name='Ada',
            last_name='Lovelace',
            primary_section=self.section,
        )
        self.month = date(2026, 6, 1)
        self.slot_one = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        self.slot_two = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(10, 0),
            end_time=time(11, 0),
            is_active=True,
        )
        self.slot_three = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.FRIDAY,
            start_time=time(11, 0),
            end_time=time(12, 0),
            is_active=True,
        )
        self.other_slot = WeeklyClassSlot.objects.create(
            section=self.other_section,
            weekday=Weekday.TUESDAY,
            start_time=time(15, 0),
            end_time=time(16, 0),
            is_active=True,
        )

    def test_assign_weekly_slots_persists_ordered_slots(self):
        plan = StudentMonthlyPlan(student=self.student, month=self.month, section=self.section, notes='Junio base')

        plan.assign_weekly_slots([self.slot_two, self.slot_one])

        plan.refresh_from_db()
        self.assertEqual(plan.month, self.month)
        self.assertEqual(list(plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')), [self.slot_two.pk, self.slot_one.pk])

    def test_assign_weekly_slots_accepts_more_than_three_when_same_section(self):
        plan = StudentMonthlyPlan(student=self.student, month=self.month, section=self.section)
        extra_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.SATURDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_active=True,
        )

        plan.assign_weekly_slots([self.slot_one, self.slot_two, self.slot_three, extra_slot])

        self.assertEqual(
            list(plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')),
            [self.slot_one.pk, self.slot_two.pk, self.slot_three.pk, extra_slot.pk],
        )

    def test_assign_weekly_slots_rejects_duplicates_and_other_section(self):
        plan = StudentMonthlyPlan(student=self.student, month=self.month, section=self.section)
        extra_slot = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.SATURDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
            is_active=True,
        )

        with self.assertRaises(ValidationError) as raised:
            plan.assign_weekly_slots([self.slot_one, self.slot_one, self.slot_three])

        message = str(raised.exception)
        self.assertIn('Monthly plan cannot include duplicate weekly slots.', message)

        with self.assertRaises(ValidationError) as raised_other_section:
            plan.assign_weekly_slots([self.slot_one, self.other_slot])

        self.assertIn('Monthly plan weekly slots must match the selected section.', str(raised_other_section.exception))

    def test_get_effective_monthly_plan_for_reuses_latest_previous_month(self):
        june_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=self.month,
            section=self.section,
            notes='Plan de junio',
        )
        june_plan.assign_weekly_slots([self.slot_one, self.slot_two])

        july_plan = self.student.get_effective_monthly_plan_for(date(2026, 7, 15))

        self.assertIsNotNone(july_plan)
        self.assertEqual(july_plan.pk, june_plan.pk)
        self.assertEqual(july_plan.month, self.month)
        self.assertEqual(
            list(july_plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')),
            [self.slot_one.pk, self.slot_two.pk],
        )

    def test_get_effective_monthly_plan_for_prefers_exact_empty_override_over_previous_month(self):
        june_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=self.month,
            section=self.section,
            notes='Plan de junio',
        )
        june_plan.assign_weekly_slots([self.slot_one, self.slot_two])
        july_month = date(2026, 7, 1)
        july_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=july_month,
            section=self.section,
            notes='Mes pausado',
        )
        july_plan.replace_weekly_slots([])

        effective_plan = self.student.get_effective_monthly_plan_for(date(2026, 7, 15))

        self.assertIsNotNone(effective_plan)
        self.assertEqual(effective_plan.pk, july_plan.pk)
        self.assertEqual(effective_plan.plan_slots.count(), 0)

    def test_get_effective_monthly_plans_for_keeps_latest_plan_per_section(self):
        june_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=self.month,
            section=self.section,
            notes='Cadillac junio',
        )
        june_plan.assign_weekly_slots([self.slot_one])
        july_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=date(2026, 7, 1),
            section=self.section,
            notes='Cadillac julio',
        )
        july_plan.assign_weekly_slots([self.slot_two])
        other_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=self.month,
            section=self.other_section,
            notes='Reformer junio',
        )
        other_plan.assign_weekly_slots([self.other_slot])

        effective_plans = self.student.get_effective_monthly_plans_for(date(2026, 7, 15))

        self.assertEqual(
            {(plan.section_id, plan.pk) for plan in effective_plans},
            {(self.section.pk, july_plan.pk), (self.other_section.pk, other_plan.pk)},
        )

    def test_session_matches_effective_monthly_plan_for_multiple_sections(self):
        cadillac_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=self.month,
            section=self.section,
        )
        cadillac_plan.assign_weekly_slots([self.slot_one])
        reformer_plan = StudentMonthlyPlan.objects.create(
            student=self.student,
            month=self.month,
            section=self.other_section,
        )
        reformer_plan.assign_weekly_slots([self.other_slot])
        matching_session = ClassSession.objects.create(
            slot=self.other_slot,
            section=self.other_section,
            date=date(2026, 6, 2),
            start_time=self.other_slot.start_time,
            end_time=self.other_slot.end_time,
            capacity=6,
            status=SessionStatus.SCHEDULED,
        )

        self.assertTrue(self.student.session_matches_effective_monthly_plan(matching_session))

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
