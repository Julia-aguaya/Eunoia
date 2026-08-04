import csv

from django.core.management.base import BaseCommand, CommandError

from scheduling.fixed_booking_repair import CandidateRepairError, repair_expected_fixed_bookings
from scheduling.models import ClassSession


CSV_COLUMNS = (
    'student_id', 'alumna', 'session_id', 'fecha', 'horario', 'sección',
    'estado_encontrado', 'acción', 'modo', 'detalle',
)


class Command(BaseCommand):
    help = 'Report or conservatively repair missing fixed-slot bookings in an inclusive date range.'

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

        try:
            rows = repair_expected_fixed_bookings(
                start_date=start_date,
                end_date=end_date,
                apply=not options['dry_run'],
            )
        except CandidateRepairError as exc:
            self.stderr.write(
                'repair_fixed_bookings pending=true '
                f'student_id={exc.student_id} session_id={exc.session_id} '
                f'attempts={exc.attempts} errno={exc.errno} detail={exc.detail}'
            )
            raise
        writer = csv.DictWriter(self.stdout, fieldnames=CSV_COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({
                **row,
                'sección': row['seccion'],
                'acción': row['accion'],
            })

        mode = 'dry-run' if options['dry_run'] else 'apply'
        actions = {}
        for row in rows:
            actions[row['accion']] = actions.get(row['accion'], 0) + 1
        summary = ', '.join(f'{action}={count}' for action, count in sorted(actions.items())) or 'sin pares esperados'
        self.stderr.write(f'repair_fixed_bookings mode={mode} total={len(rows)} {summary}')

    @staticmethod
    def parse_date(value):
        try:
            return ClassSession._meta.get_field('date').to_python(value)
        except Exception as exc:
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.') from exc
