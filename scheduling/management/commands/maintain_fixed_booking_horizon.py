from datetime import timedelta
import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from scheduling.fixed_booking_repair import repair_expected_fixed_bookings
from scheduling.fixed_booking_capacity import assess_fixed_capacity, record_fixed_capacity_conflict
from scheduling.models import ClassSession
from scheduling.use_cases import generate_class_sessions


class Command(BaseCommand):
    help = 'Generate and reconcile a future horizon of fixed bookings.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=int(os.getenv('EUNOIA_FIXED_BOOKING_HORIZON_DAYS', '42')),
            help='Inclusive future horizon beginning today (default: 42).',
        )

    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        if days_ahead < 1:
            raise CommandError('--days-ahead must be at least 1.')

        start_date = timezone.localdate()
        end_date = start_date + timedelta(days=days_ahead - 1)
        generated = generate_class_sessions(start_date=start_date, end_date=end_date)
        repaired = repair_expected_fixed_bookings(
            start_date=start_date,
            end_date=end_date,
            apply=True,
        )
        actions = {}
        for row in repaired:
            actions[row['accion']] = actions.get(row['accion'], 0) + 1
            if row['accion'] == 'SKIP_CAPACITY':
                session = ClassSession.objects.get(pk=row['session_id'])
                assessment = assess_fixed_capacity(session=session)
                record_fixed_capacity_conflict(
                    session=session,
                    assessment=assessment,
                    detail='Una reserva fija valida no pudo materializarse por capacidad.',
                )
        summary = ', '.join(f'{action}={count}' for action, count in sorted(actions.items())) or 'sin pares esperados'
        unresolved = sum(
            1 for row in repaired if row['accion'] in {'SKIP_CAPACITY', 'FIXED_CAPACITY_CONFLICT', 'ERROR'}
        )
        self.stdout.write(
            f'fixed_booking_maintenance start={start_date.isoformat()} end={end_date.isoformat()} '
            f'sessions_created={generated.created_count} sessions_skipped={generated.skipped_duplicates} {summary}'
        )
        if unresolved:
            raise CommandError(f'fixed_booking_maintenance unresolved_conflicts={unresolved}')
