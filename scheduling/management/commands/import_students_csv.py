from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scheduling.student_import import StudentImportValidationError, import_students_from_csv


class Command(BaseCommand):
    help = 'Import or update student users from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Path to the CSV file exported from Excel or similar tools.')

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path'])
        if not csv_path.exists() or not csv_path.is_file():
            raise CommandError(f'CSV file not found: {csv_path}')

        try:
            with csv_path.open('r', encoding='utf-8-sig', newline='') as csv_file:
                result = import_students_from_csv(csv_file)
        except StudentImportValidationError as exc:
            raise CommandError(str(exc)) from exc
        except OSError as exc:
            raise CommandError(f'Could not read CSV file: {exc}') from exc

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed: {result.processed_count} rows processed, '
                f'{result.created_count} users created, {result.updated_count} users updated.'
            )
        )
