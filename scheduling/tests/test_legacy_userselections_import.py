import csv
import json
import tempfile
from datetime import date, time
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from scheduling.legacy_userselections_import import (
    build_confirmed_section_candidates_by_weekday_and_time,
    import_legacy_userselections_from_json,
)
from scheduling.legacy_userselections_manual_backfill import (
    import_legacy_userselections_manual_backfill_from_csv,
)
from scheduling.models import Section, StudentMonthlyPlan, User, Weekday, WeeklyClassSlot


class LegacyUserSelectionsImportTests(TestCase):
    def setUp(self):
        self.section = Section.objects.get(code='cadillac')
        self.student = User.objects.create_user(
            email='selection-student@example.com',
            password='SelectionStudent2026!',
            first_name='Ada',
            last_name='Lovelace',
            role='student',
            primary_section=self.section,
            notes='[legacy-user-import]\nlegacy_user_id=legacy-student-1\n[/legacy-user-import]',
        )
        self.monday_nine = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        self.wednesday_nine = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.WEDNESDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        self.thursday_nine = WeeklyClassSlot.objects.create(
            section=self.section,
            weekday=Weekday.THURSDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )

    def test_import_preserves_current_month_override_and_future_original_plan(self):
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-1'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Lunes', 'hour': '09:00'},
                        {'day': 'Miércoles', 'hour': '09:00'},
                    ],
                    'temporarySelections': [
                        {'day': 'Jueves', 'hour': '09:00'},
                    ],
                    'changesThisMonth': 1,
                    'lastChange': {'$date': '2026-06-22T19:06:27.519Z'},
                }
            ]
        )

        result = import_legacy_userselections_from_json(json_path=json_path)

        self.assertEqual(result.cutoff_month, date(2026, 6, 1))
        self.assertEqual(result.created_plan_count, 2)
        self.assertEqual(StudentMonthlyPlan.objects.filter(student=self.student).count(), 2)

        june_plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 6, 1))
        july_plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 7, 1))

        self.assertEqual(
            list(june_plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')),
            [self.thursday_nine.pk],
        )
        self.assertEqual(
            list(july_plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')),
            [self.monday_nine.pk, self.wednesday_nine.pk],
        )

        second_result = import_legacy_userselections_from_json(json_path=json_path)

        self.assertEqual(second_result.created_plan_count, 0)
        self.assertEqual(second_result.updated_plan_count, 0)
        self.assertEqual(second_result.unchanged_plan_count, 2)

    def test_placeholder_temporary_selection_is_ignored(self):
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-2'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Lunes', 'hour': '09:00'},
                    ],
                    'temporarySelections': [
                        {'day': '__placeholder__', 'hour': '__none__'},
                    ],
                    'changesThisMonth': 2,
                    'lastChange': {'$date': '2026-06-10T10:00:00.000Z'},
                }
            ]
        )

        result = import_legacy_userselections_from_json(json_path=json_path)

        self.assertEqual(result.created_plan_count, 1)
        self.assertEqual(StudentMonthlyPlan.objects.filter(student=self.student).count(), 1)
        june_plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 6, 1))
        self.assertEqual(
            list(june_plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position')),
            [self.monday_nine.pk],
        )

    def test_confirmed_section_map_creates_missing_slots_for_unique_intersection(self):
        self.student.primary_section = None
        self.student.save(update_fields=['primary_section', 'updated_at'])

        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-3'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Lunes', 'hour': '10:00'},
                        {'day': 'Viernes', 'hour': '19:00'},
                    ],
                    'temporarySelections': [],
                    'changesThisMonth': 0,
                    'lastChange': {'$date': '2026-06-15T10:00:00.000Z'},
                }
            ]
        )

        result = import_legacy_userselections_from_json(
            json_path=json_path,
            section_candidates_by_slot=build_confirmed_section_candidates_by_weekday_and_time(),
            create_missing_slots=True,
        )

        self.assertEqual(result.created_plan_count, 1)
        self.assertEqual(result.created_slot_count, 2)
        self.assertEqual(result.resolved_by_slot_intersection_count, 1)
        june_plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 6, 1))
        self.assertEqual(june_plan.section.code, 'reformer_abajo')
        self.assertEqual(
            list(june_plan.plan_slots.values_list('weekly_class_slot__section__code', 'weekly_class_slot__weekday', 'weekly_class_slot__start_time').order_by('position')),
            [
                ('reformer_abajo', Weekday.MONDAY, time(10, 0)),
                ('reformer_abajo', Weekday.FRIDAY, time(19, 0)),
            ],
        )

    def test_confirmed_section_map_skips_ambiguous_specs_when_requested(self):
        self.student.primary_section = None
        self.student.save(update_fields=['primary_section', 'updated_at'])

        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-4'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Martes', 'hour': '09:00'},
                    ],
                    'temporarySelections': [],
                    'changesThisMonth': 0,
                    'lastChange': {'$date': '2026-06-15T10:00:00.000Z'},
                }
            ]
        )

        result = import_legacy_userselections_from_json(
            json_path=json_path,
            section_candidates_by_slot=build_confirmed_section_candidates_by_weekday_and_time(),
            create_missing_slots=True,
            skip_unresolved_sections=True,
        )

        self.assertEqual(result.created_plan_count, 0)
        self.assertEqual(result.unresolved_section_count, 1)
        self.assertEqual(result.ambiguous_section_count, 1)
        self.assertEqual(StudentMonthlyPlan.objects.filter(student=self.student).count(), 0)

    def test_confirmed_section_map_reuses_unique_resolution_from_same_record(self):
        self.student.primary_section = None
        self.student.save(update_fields=['primary_section', 'updated_at'])

        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-5'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Viernes', 'hour': '18:00'},
                    ],
                    'temporarySelections': [
                        {'day': 'Viernes', 'hour': '19:00'},
                    ],
                    'changesThisMonth': 1,
                    'lastChange': {'$date': '2026-06-20T10:00:00.000Z'},
                }
            ]
        )

        result = import_legacy_userselections_from_json(
            json_path=json_path,
            section_candidates_by_slot=build_confirmed_section_candidates_by_weekday_and_time(),
            create_missing_slots=True,
        )

        self.assertEqual(result.created_plan_count, 2)
        self.assertEqual(result.resolved_by_slot_intersection_count, 1)
        self.assertEqual(result.resolved_by_inferred_section_count, 1)

        june_plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 6, 1))
        july_plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 7, 1))
        self.assertEqual(june_plan.section.code, 'reformer_abajo')
        self.assertEqual(july_plan.section.code, 'reformer_abajo')

    def _write_json(self, payload):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / 'userselections.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path


class LegacyUserSelectionsManualBackfillTests(TestCase):
    def setUp(self):
        self.cadillac = Section.objects.get(code='cadillac')
        self.reformer_abajo = Section.objects.get(code='reformer_abajo')
        self.student = User.objects.create_user(
            email='manual-backfill@example.com',
            password='ManualBackfill2026!',
            first_name='Grace',
            last_name='Hopper',
            role='student',
            notes='[legacy-user-import]\nlegacy_user_id=legacy-student-1\n[/legacy-user-import]',
        )

    def test_manual_backfill_normalizes_resolved_section_and_creates_pending_plan(self):
        WeeklyClassSlot.objects.create(
            section=self.reformer_abajo,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-1'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Lunes', 'hour': '09:00'},
                    ],
                    'temporarySelections': [],
                    'changesThisMonth': 0,
                    'lastChange': {'$date': '2026-06-15T10:00:00.000Z'},
                }
            ]
        )
        csv_path = self._write_csv(
            [
                {
                    'student_email': self.student.email,
                    'student_name': self.student.get_full_name(),
                    'student_id': str(self.student.id),
                    'legacy_user_id': 'legacy-student-1',
                    'legacy_userselection_id': 'legacy-selection-1',
                    'source_index': '1',
                    'month': '2026-06-01',
                    'selection_kind': 'original',
                    'status': 'ambiguous',
                    'possible_sections': 'reformer_abajo | reformer_arriba',
                    '': '',
                    'resolved_section': 'refomer_abajo',
                }
            ]
        )

        result = import_legacy_userselections_manual_backfill_from_csv(
            csv_path=csv_path,
            json_path=json_path,
        )

        self.assertEqual(result.resolution_column, 'resolved_section')
        self.assertEqual(result.normalized_resolution_count, 1)
        self.assertEqual(result.created_plan_count, 1)
        plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 6, 1))
        self.assertEqual(plan.section, self.reformer_abajo)

    def test_manual_backfill_rejects_resolution_outside_possible_sections(self):
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-2'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Lunes', 'hour': '08:00'},
                    ],
                    'temporarySelections': [],
                    'changesThisMonth': 0,
                    'lastChange': {'$date': '2026-06-15T10:00:00.000Z'},
                }
            ]
        )
        csv_path = self._write_csv(
            [
                {
                    'student_email': self.student.email,
                    'student_name': self.student.get_full_name(),
                    'student_id': str(self.student.id),
                    'legacy_user_id': 'legacy-student-1',
                    'legacy_userselection_id': 'legacy-selection-2',
                    'source_index': '1',
                    'month': '2026-06-01',
                    'selection_kind': 'original',
                    'status': 'ambiguous',
                    'possible_sections': 'reformer_abajo | reformer_arriba',
                    '': '',
                    'resolved_section': 'cadillac',
                }
            ]
        )

        with self.assertRaisesMessage(
            Exception,
            'resolved section cadillac is not among possible_sections (reformer_abajo, reformer_arriba).',
        ):
            import_legacy_userselections_manual_backfill_from_csv(
                csv_path=csv_path,
                json_path=json_path,
            )

        self.assertFalse(StudentMonthlyPlan.objects.exists())

    def test_manual_backfill_allows_explicit_override_outside_possible_sections(self):
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-selection-3'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalSelections': [
                        {'day': 'Lunes', 'hour': '08:00'},
                    ],
                    'temporarySelections': [],
                    'changesThisMonth': 0,
                    'lastChange': {'$date': '2026-06-15T10:00:00.000Z'},
                }
            ]
        )
        csv_path = self._write_csv(
            [
                {
                    'student_email': self.student.email,
                    'student_name': self.student.get_full_name(),
                    'student_id': str(self.student.id),
                    'legacy_user_id': 'legacy-student-1',
                    'legacy_userselection_id': 'legacy-selection-3',
                    'source_index': '1',
                    'month': '2026-06-01',
                    'selection_kind': 'original',
                    'status': 'ambiguous',
                    'possible_sections': 'reformer_abajo | reformer_arriba',
                    '': '',
                    'resolved_section': 'cadillac',
                    'manual_override': 'true',
                    'manual_override_reason': 'Business approved cadillac override',
                }
            ]
        )

        result = import_legacy_userselections_manual_backfill_from_csv(
            csv_path=csv_path,
            json_path=json_path,
            create_missing_slots=True,
        )

        self.assertEqual(result.manual_override_count, 1)
        plan = StudentMonthlyPlan.objects.get(student=self.student, month=date(2026, 6, 1))
        self.assertEqual(plan.section, self.cadillac)
        self.assertIn('manual_override=true', plan.notes)
        self.assertIn('manual_override_section=cadillac', plan.notes)
        self.assertIn('manual_override_reason=Business approved cadillac override', plan.notes)

    def test_command_reports_manual_backfill_counts(self):
        WeeklyClassSlot.objects.create(
            section=self.reformer_abajo,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
        )
        payload = [
            {
                '_id': {'$oid': 'legacy-selection-command'},
                'user': {'$oid': 'legacy-student-1'},
                'originalSelections': [
                    {'day': 'Lunes', 'hour': '09:00'},
                ],
                'temporarySelections': [],
                'changesThisMonth': 0,
                'lastChange': {'$date': '2026-06-15T10:00:00.000Z'},
            },
        ]
        csv_rows = [
            {
                'student_email': self.student.email,
                'student_name': self.student.get_full_name(),
                'student_id': str(self.student.id),
                'legacy_user_id': 'legacy-student-1',
                'legacy_userselection_id': 'legacy-selection-command',
                'source_index': '1',
                'month': '2026-06-01',
                'selection_kind': 'original',
                'status': 'ambiguous',
                'possible_sections': 'reformer_abajo | reformer_arriba',
                '': '',
                'resolved_section': 'refomer_abajo',
            }
        ]

        with tempfile.NamedTemporaryFile('w', suffix='.json', encoding='utf-8', delete=False) as handle:
            json.dump(payload, handle)
            json_path = Path(handle.name)
        csv_path = self._write_csv(csv_rows)

        out = tempfile.SpooledTemporaryFile(mode='w+')
        call_command(
            'import_legacy_userselections_manual_backfill_csv',
            str(csv_path),
            str(json_path),
            stdout=out,
        )
        out.seek(0)
        output = out.read()

        self.assertIn('1 CSV rows scanned via `resolved_section`', output)
        self.assertIn('1 plans created, 0 updated, 0 unchanged', output)

    def _write_json(self, payload):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / 'userselections.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path

    def _write_csv(self, rows):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / 'manual-resolution.csv'
        fieldnames = [
            'student_email',
            'student_name',
            'student_id',
            'legacy_user_id',
            'legacy_userselection_id',
            'source_index',
            'month',
            'selection_kind',
            'status',
            'possible_sections',
            '',
            'resolved_section',
            'manual_override',
            'manual_override_reason',
        ]
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path
