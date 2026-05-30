from django.core.management.base import BaseCommand, CommandError

from scheduling.models import ClassSession
from scheduling.use_cases import generate_class_sessions


class Command(BaseCommand):
    help = 'Generate class sessions from weekly slots for a date range.'

    def add_arguments(self, parser):
        parser.add_argument('start_date', type=self.parse_date)
        parser.add_argument('end_date', type=self.parse_date)
        parser.add_argument(
            '--section',
            dest='section_code',
            help='Filter weekly slots by section code.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without creating sessions.',
        )

    def handle(self, *args, **options):
        start_date = options['start_date']
        end_date = options['end_date']
        section_code = options.get('section_code')
        dry_run = options['dry_run']

        try:
            result = generate_class_sessions(
                start_date=start_date,
                end_date=end_date,
                section_code=section_code,
                dry_run=dry_run,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        action_label = 'Would create' if dry_run else 'Created'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action_label} {result.created_count} sessions '
                f'from {result.inspected_matches} matching weekly slots.'
            )
        )
        self.stdout.write(f'Skipped duplicates: {result.skipped_duplicates}')

    @staticmethod
    def parse_date(value):
        try:
            return ClassSession._meta.get_field('date').to_python(value)
        except Exception as exc:
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.') from exc
