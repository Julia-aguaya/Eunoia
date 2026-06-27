from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scheduling.legacy_user_import import LegacyUserImportValidationError, import_legacy_users_from_json


class Command(BaseCommand):
    help = 'Import or update users from the legacy Mongo JSON export.'

    def add_arguments(self, parser):
        parser.add_argument('json_path', help='Path to the legacy users JSON export.')
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='Also reset temporary passwords for users that already exist in Django.',
        )
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
            result = import_legacy_users_from_json(
                json_path=json_path,
                reset_passwords=options['reset_passwords'],
                dry_run=options['dry_run'],
            )
        except LegacyUserImportValidationError as exc:
            raise CommandError(str(exc)) from exc

        mode_label = 'Dry run completed' if options['dry_run'] else 'Import completed'
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode_label}: {result.processed_count} users processed, '
                f'{result.created_count} created, {result.updated_count} updated, '
                f'{result.password_reset_count} temporary passwords assigned, '
                f'{result.activated_access_count} monthly access records activated.'
            )
        )
