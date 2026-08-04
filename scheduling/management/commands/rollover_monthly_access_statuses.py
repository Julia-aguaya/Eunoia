from datetime import datetime
import re

from django.core.management.base import BaseCommand, CommandError

from scheduling.use_cases import rollover_monthly_access_statuses


class Command(BaseCommand):
    help = (
        'Create active monthly access for every globally active student. '
        'Existing target-month access rows are never changed.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            required=True,
            help='Target month in YYYY-MM format.',
        )

    def handle(self, *args, **options):
        month = self.parse_month(options['month'])
        result = rollover_monthly_access_statuses(month=month)

        for failure in result.failures:
            self.stderr.write(
                'Rollover failure: '
                f'month={result.month:%Y-%m}; student_id={failure.student_id}; error={failure.error}'
            )

        summary = (
            'Rollover summary: '
            f'month={result.month:%Y-%m}; '
            f'students evaluated={result.evaluated_count}; '
            f'accesses created={result.created_count}; '
            f'existing accesses={result.skipped_existing_count}; '
            f'skipped due to global deactivation={result.skipped_inactive_count}; '
            f'errors/failures={len(result.failures)}.'
        )
        if result.failures:
            self.stderr.write(f'{summary} Rollover completed with failures.')
            raise CommandError('Rollover completed with partial failures.')

        self.stdout.write(self.style.SUCCESS(f'{summary} Rollover completed.'))

    @staticmethod
    def parse_month(value):
        if not re.fullmatch(r'\d{4}-\d{2}', value):
            raise CommandError(f'Invalid month "{value}". Use YYYY-MM.')
        try:
            return datetime.strptime(value, '%Y-%m').date()
        except ValueError as exc:
            raise CommandError(f'Invalid month "{value}". Use YYYY-MM.') from exc
