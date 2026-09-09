import csv

from django.core.management.base import BaseCommand, CommandError

from scheduling.access_remediation import remediate_automatic_access_impact
from scheduling.models import ClassSession


class Command(BaseCommand):
    help = 'Dry-run by default: restore only proven automatic or explicitly approved legacy booking cancellations.'

    def add_arguments(self, parser):
        parser.add_argument('--start-date', required=True, type=self.parse_date)
        parser.add_argument('--end-date', required=True, type=self.parse_date)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--dry-run', action='store_true', default=True)
        mode.add_argument('--apply', action='store_false', dest='dry_run')

    def handle(self, *args, **options):
        start_date = options['start_date']
        end_date = options['end_date']
        if end_date < start_date:
            raise CommandError('--end-date must be on or after --start-date.')
        rows = remediate_automatic_access_impact(
            start_date=start_date,
            end_date=end_date,
            apply=not options['dry_run'],
        )
        writer = csv.DictWriter(self.stdout, fieldnames=('student_id', 'booking_id', 'action', 'mode'))
        writer.writeheader()
        writer.writerows(rows)
        actions = {}
        for row in rows:
            actions[row['action']] = actions.get(row['action'], 0) + 1
        summary = ', '.join(f'{action}={count}' for action, count in sorted(actions.items())) or 'no changes'
        self.stderr.write(f'remediate_automatic_access_impact mode={"dry-run" if options["dry_run"] else "apply"} {summary}')

    @staticmethod
    def parse_date(value):
        try:
            return ClassSession._meta.get_field('date').to_python(value)
        except Exception as exc:
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.') from exc
