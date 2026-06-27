import json
import tempfile
from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from scheduling.legacy_recoverableturns_import import import_legacy_recoverableturns_from_json
from scheduling.models import RecoveryCredit, RecoveryCreditSource, RecoveryCreditStatus, Section, StudentMonthlyPlan, User


class LegacyRecoverableTurnsImportTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            email='recoverable@example.com',
            password='RecoverableStudent2026!',
            first_name='Ada',
            last_name='Lovelace',
            role='student',
            notes='[legacy-user-import]\nlegacy_user_id=legacy-student-1\n[/legacy-user-import]',
        )

    def test_import_creates_only_safe_manual_recovery_credits(self):
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-turn-expired'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Lunes',
                    'originalHour': '10:00',
                    'cancelledWeek': {'$date': '2020-01-06T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
                {
                    '_id': {'$oid': 'legacy-turn-used'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Viernes',
                    'originalHour': '19:00',
                    'cancelledWeek': {'$date': '2020-01-10T15:00:00.000Z'},
                    'recovered': True,
                    'recoveryDate': {'$date': '2020-01-17T15:00:00.000Z'},
                    'assignedDay': 'Martes',
                    'assignedHour': '20:00',
                },
                {
                    '_id': {'$oid': 'legacy-turn-ambiguous'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Martes',
                    'originalHour': '09:00',
                    'cancelledWeek': {'$date': '2020-01-13T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
                {
                    '_id': {'$oid': 'legacy-turn-missing-user'},
                    'user': {'$oid': 'missing-student'},
                    'originalDay': 'Lunes',
                    'originalHour': '20:00',
                    'cancelledWeek': {'$date': '2020-01-20T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
                {
                    '_id': {'$oid': 'legacy-turn-inconsistent'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Jueves',
                    'originalHour': '20:00',
                    'cancelledWeek': {'$date': '2020-01-27T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': {'$date': '2020-02-03T15:00:00.000Z'},
                    'assignedDay': 'Martes',
                    'assignedHour': '20:00',
                },
            ]
        )
        result = import_legacy_recoverableturns_from_json(json_path=json_path)

        self.assertEqual(result.total_records, 5)
        self.assertEqual(result.matched_user_count, 4)
        self.assertEqual(result.created_count, 2)
        self.assertEqual(result.unchanged_count, 0)
        self.assertEqual(result.skipped_missing_user_count, 1)
        self.assertEqual(result.skipped_ambiguous_section_count, 1)
        self.assertEqual(result.skipped_inconsistent_state_count, 1)
        self.assertEqual(result.imported_expired_count, 1)
        self.assertEqual(result.imported_used_count, 1)

        expired_credit = RecoveryCredit.objects.get(notes__contains='legacy-turn-expired')
        used_credit = RecoveryCredit.objects.get(notes__contains='legacy-turn-used')

        self.assertEqual(expired_credit.student, self.student)
        self.assertEqual(expired_credit.section.code, 'reformer_abajo')
        self.assertEqual(expired_credit.source, RecoveryCreditSource.MANUAL)
        self.assertEqual(expired_credit.status, RecoveryCreditStatus.EXPIRED)
        self.assertEqual(expired_credit.expires_at, date(2020, 4, 6))

        self.assertEqual(used_credit.status, RecoveryCreditStatus.USED)
        self.assertEqual(used_credit.used_at.date(), date(2020, 1, 17))
        self.assertEqual(used_credit.section.code, 'reformer_abajo')

    def test_import_is_idempotent_for_same_legacy_turn(self):
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-turn-repeat'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Lunes',
                    'originalHour': '20:00',
                    'cancelledWeek': {'$date': '2020-01-06T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
            ]
        )

        first_result = import_legacy_recoverableturns_from_json(json_path=json_path)
        second_result = import_legacy_recoverableturns_from_json(json_path=json_path)

        self.assertEqual(first_result.created_count, 1)
        self.assertEqual(second_result.created_count, 0)
        self.assertEqual(second_result.unchanged_count, 1)
        self.assertEqual(RecoveryCredit.objects.filter(notes__contains='legacy-turn-repeat').count(), 1)

    def test_command_reports_partial_safe_import(self):
        payload = [
            {
                '_id': {'$oid': 'legacy-turn-command'},
                'user': {'$oid': 'legacy-student-1'},
                'originalDay': 'Lunes',
                'originalHour': '10:00',
                'cancelledWeek': {'$date': '2020-01-06T15:00:00.000Z'},
                'recovered': False,
                'recoveryDate': None,
                'assignedDay': None,
                'assignedHour': None,
            },
        ]

        with tempfile.NamedTemporaryFile('w', suffix='.json', encoding='utf-8', delete=False) as handle:
            json.dump(payload, handle)
            json_path = Path(handle.name)

        out = tempfile.SpooledTemporaryFile(mode='w+')
        call_command('import_legacy_recoverableturns_json', str(json_path), stdout=out)
        out.seek(0)
        output = out.read()

        self.assertIn('1 created, 0 unchanged', output)
        self.assertIn('0 skipped for unresolved section', output)

    def test_import_resolves_ambiguous_section_from_current_activity(self):
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=timezone.localdate().replace(day=1),
            section=Section.objects.get(code='reformer_abajo'),
        )
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-turn-current-activity'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Martes',
                    'originalHour': '09:00',
                    'cancelledWeek': {'$date': '2026-05-10T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
            ]
        )

        result = import_legacy_recoverableturns_from_json(json_path=json_path)

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.resolved_by_current_activity_count, 1)
        credit = RecoveryCredit.objects.get(notes__contains='legacy-turn-current-activity')
        self.assertEqual(credit.section.code, 'reformer_abajo')

    def test_import_keeps_unresolved_ambiguous_section_blocked(self):
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=timezone.localdate().replace(day=1),
            section=Section.objects.get(code='cadillac'),
        )
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-turn-still-ambiguous'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Viernes',
                    'originalHour': '18:00',
                    'cancelledWeek': {'$date': '2026-05-10T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
            ]
        )

        result = import_legacy_recoverableturns_from_json(json_path=json_path)

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.resolved_by_current_activity_count, 0)
        self.assertEqual(result.skipped_ambiguous_section_count, 1)
        self.assertFalse(RecoveryCredit.objects.filter(notes__contains='legacy-turn-still-ambiguous').exists())

    def test_import_revokes_previously_imported_invalid_ambiguous_credit(self):
        cadillac = Section.objects.get(code='cadillac')
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=timezone.localdate().replace(day=1),
            section=cadillac,
        )
        existing_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=cadillac,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=date(2026, 8, 10),
            notes=(
                '[legacy-recoverableturns-import]\n'
                'source=eunoia.recoverableturns.json\n'
                'legacy_recoverableturn_id=legacy-turn-invalid-existing\n'
                'legacy_user_id=legacy-student-1\n'
                'legacy_original_day=Viernes\n'
                'legacy_original_hour=18:00\n'
                'legacy_cancelled_week=2026-05-10T15:00:00+00:00\n'
                'legacy_recovered=false\n'
                'legacy_recovery_date=\n'
                'legacy_assigned_day=\n'
                'legacy_assigned_hour=\n'
                '[/legacy-recoverableturns-import]'
            ),
        )
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-turn-invalid-existing'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Viernes',
                    'originalHour': '18:00',
                    'cancelledWeek': {'$date': '2026-05-10T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
            ]
        )

        result = import_legacy_recoverableturns_from_json(json_path=json_path)

        existing_credit.refresh_from_db()
        self.assertEqual(result.revoked_invalid_section_count, 1)
        self.assertEqual(result.skipped_ambiguous_section_count, 1)
        self.assertEqual(existing_credit.status, RecoveryCreditStatus.REVOKED)
        self.assertIn('Legacy import revoked', existing_credit.notes)

    def test_dry_run_does_not_persist_revocation_of_invalid_ambiguous_credit(self):
        cadillac = Section.objects.get(code='cadillac')
        StudentMonthlyPlan.objects.create(
            student=self.student,
            month=timezone.localdate().replace(day=1),
            section=cadillac,
        )
        existing_credit = RecoveryCredit.objects.create(
            student=self.student,
            section=cadillac,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            expires_at=date(2026, 8, 10),
            notes=(
                '[legacy-recoverableturns-import]\n'
                'source=eunoia.recoverableturns.json\n'
                'legacy_recoverableturn_id=legacy-turn-invalid-dry-run\n'
                'legacy_user_id=legacy-student-1\n'
                'legacy_original_day=Viernes\n'
                'legacy_original_hour=18:00\n'
                'legacy_cancelled_week=2026-05-10T15:00:00+00:00\n'
                'legacy_recovered=false\n'
                'legacy_recovery_date=\n'
                'legacy_assigned_day=\n'
                'legacy_assigned_hour=\n'
                '[/legacy-recoverableturns-import]'
            ),
        )
        json_path = self._write_json(
            [
                {
                    '_id': {'$oid': 'legacy-turn-invalid-dry-run'},
                    'user': {'$oid': 'legacy-student-1'},
                    'originalDay': 'Viernes',
                    'originalHour': '18:00',
                    'cancelledWeek': {'$date': '2026-05-10T15:00:00.000Z'},
                    'recovered': False,
                    'recoveryDate': None,
                    'assignedDay': None,
                    'assignedHour': None,
                },
            ]
        )

        result = import_legacy_recoverableturns_from_json(json_path=json_path, dry_run=True)

        existing_credit.refresh_from_db()
        self.assertEqual(result.revoked_invalid_section_count, 1)
        self.assertEqual(existing_credit.status, RecoveryCreditStatus.AVAILABLE)
        self.assertNotIn('Legacy import revoked', existing_credit.notes)

    def _write_json(self, payload):
        with tempfile.NamedTemporaryFile('w', suffix='.json', encoding='utf-8', delete=False) as handle:
            json.dump(payload, handle)
            return Path(handle.name)
