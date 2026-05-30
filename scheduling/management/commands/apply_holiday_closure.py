from django.core.management.base import BaseCommand, CommandError

from scheduling.models import HolidayClosure
from scheduling.use_cases import apply_holiday_closure


class Command(BaseCommand):
    help = 'Apply a full-day holiday closure and process recovery credits.'

    def add_arguments(self, parser):
        parser.add_argument('date', type=self.parse_date)
        parser.add_argument(
            '--reason',
            help='Reason used when creating the holiday closure if it does not exist yet.',
        )
        parser.add_argument(
            '--notes',
            default='',
            help='Optional operational notes when creating the closure.',
        )

    def handle(self, *args, **options):
        closure_date = options['date']
        reason = options.get('reason')
        notes = options.get('notes', '')

        existing_closure = HolidayClosure.objects.filter(date=closure_date).first()
        if existing_closure is None and not reason:
            raise CommandError('A closure for this date does not exist. Provide --reason to create it.')

        effective_reason = reason if existing_closure is None else existing_closure.reason
        effective_notes = notes if existing_closure is None else existing_closure.notes

        application = apply_holiday_closure(
            closure_date=closure_date,
            reason=effective_reason,
            notes=effective_notes,
        )
        closure = application.closure
        result = application.result
        action = 'Created and applied' if application.created else 'Applied'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} holiday closure for {closure.date}: '
                f'{result["updated_sessions"]} sessions updated, '
                f'{result["created_credits"]} recovery credits created, '
                f'{result["existing_credits"]} already existed.'
            )
        )

    @staticmethod
    def parse_date(value):
        try:
            return HolidayClosure._meta.get_field('date').to_python(value)
        except Exception as exc:
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.') from exc
