from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scheduling.legacy_userselections_import import LegacyUserSelectionsImportValidationError
from scheduling.legacy_userselections_manual_backfill import (
    import_legacy_userselections_manual_backfill_from_csv,
)


class Command(BaseCommand):
    help = (
        'Backfill only manually resolved pending legacy userselections cases from a curated CSV report. '
        'Rows are validated against the legacy JSON and current students before any write.'
    )

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Path to the curated ambiguous userselections CSV report.')
        parser.add_argument('json_path', help='Path to the legacy userselections JSON export.')
        parser.add_argument(
            '--create-missing-slots',
            action='store_true',
            help='Create or reactivate missing WeeklyClassSlot rows for the manually resolved section.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and simulate the backfill without persisting changes.',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path'])
        json_path = Path(options['json_path'])
        if not csv_path.exists() or not csv_path.is_file():
            raise CommandError(f'CSV file not found: {csv_path}')
        if not json_path.exists() or not json_path.is_file():
            raise CommandError(f'JSON file not found: {json_path}')

        try:
            result = import_legacy_userselections_manual_backfill_from_csv(
                csv_path=csv_path,
                json_path=json_path,
                create_missing_slots=options['create_missing_slots'],
                dry_run=options['dry_run'],
            )
        except LegacyUserSelectionsImportValidationError as exc:
            raise CommandError(str(exc)) from exc

        mode_label = 'Dry run completed' if options['dry_run'] else 'Backfill completed'
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode_label}: {result.scanned_case_count} CSV rows scanned via '
                f'`{result.resolution_column}`; {result.normalized_resolution_count} '
                f'resolution values normalized; {result.manual_override_count} manual overrides '
                f'accepted via `{result.manual_override_column or "manual_override"}`; '
                f'{result.pending_case_count} pending ambiguous cases processed; '
                f'{result.created_plan_count} plans created, {result.updated_plan_count} updated, '
                f'{result.unchanged_plan_count} unchanged; {result.created_slot_count} weekly slots created; '
                f'{result.skipped_existing_plan_count} existing legacy plans revisited idempotently.'
            )
        )
