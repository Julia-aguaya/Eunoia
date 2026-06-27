from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scheduling.legacy_recoverableturns_import import (
    LegacyRecoverableTurnsImportValidationError,
    import_legacy_recoverableturns_from_json,
)


class Command(BaseCommand):
    help = (
        'Import safely mappable legacy recoverable turns into manual RecoveryCredit rows. '
        'Ambiguous slots are resolved with the student current activity when possible; '
        'records with missing users, unresolved sections, missing slot mapping, or inconsistent state are skipped.'
    )

    def add_arguments(self, parser):
        parser.add_argument('json_path', help='Path to the legacy recoverable turns JSON export.')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and simulate the import without persisting changes.',
        )

    def handle(self, *args, **options):
        json_path = Path(options['json_path'])
        if not json_path.exists() or not json_path.is_file():
            raise CommandError(f'JSON file not found: {json_path}')

        try:
            result = import_legacy_recoverableturns_from_json(
                json_path=json_path,
                dry_run=options['dry_run'],
            )
        except LegacyRecoverableTurnsImportValidationError as exc:
            raise CommandError(str(exc)) from exc

        mode_label = 'Dry run completed' if options['dry_run'] else 'Import completed'
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode_label}: {result.total_records} records scanned; '
                f'{result.matched_user_count} matched imported students; '
                f'{result.created_count} created, {result.unchanged_count} unchanged; '
                f'{result.resolved_by_current_activity_count} ambiguous rows resolved by current activity; '
                f'{result.revoked_invalid_section_count} invalid previously imported rows revoked; '
                f'{result.imported_available_count} available, {result.imported_expired_count} expired, '
                f'{result.imported_used_count} used credits in the safe subset; '
                f'{result.skipped_missing_user_count} skipped for missing user, '
                f'{result.skipped_ambiguous_section_count} skipped for unresolved section, '
                f'{result.skipped_missing_mapping_count} skipped for missing slot mapping, '
                f'{result.skipped_inconsistent_state_count} skipped for inconsistent recovery state.'
            )
        )
