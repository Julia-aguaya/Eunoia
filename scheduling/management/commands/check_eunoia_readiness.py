from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from scheduling.models import ClassSession, Section, User, UserRole, WeeklyClassSlot


REQUIRED_SECTION_CODES = ('reformer_arriba', 'reformer_abajo', 'cadillac')


class Command(BaseCommand):
    help = 'Check the minimum data required for a local handoff or demo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit with error when any required readiness check fails.',
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        staff_count = User.objects.filter(is_active=True, is_staff=True).count()
        admin_count = User.objects.filter(is_active=True, role=UserRole.ADMIN).count()
        student_count = User.objects.filter(is_active=True, role=UserRole.STUDENT).count()
        active_section_codes = set(
            Section.objects.filter(is_active=True).values_list('code', flat=True)
        )
        missing_sections = [code for code in REQUIRED_SECTION_CODES if code not in active_section_codes]
        weekly_slot_count = WeeklyClassSlot.objects.filter(is_active=True).count()
        future_session_count = ClassSession.objects.filter(date__gte=today).exclude(status='cancelled').count()

        failures = []
        if staff_count == 0:
            failures.append('No active staff users found.')
        if admin_count == 0:
            failures.append('No active admin users found.')
        if missing_sections:
            failures.append(f'Missing active base sections: {", ".join(missing_sections)}.')
        if weekly_slot_count == 0 and future_session_count == 0:
            failures.append('No active weekly slots or future sessions found.')

        lines = [
            f'staff_active={staff_count}',
            f'admins_active={admin_count}',
            f'students_active={student_count}',
            f'sections_active={len(active_section_codes)}',
            f'weekly_slots_active={weekly_slot_count}',
            f'future_sessions={future_session_count}',
        ]
        if missing_sections:
            lines.append(f'missing_sections={", ".join(missing_sections)}')

        if failures:
            self.stdout.write(self.style.WARNING('Readiness check: FAIL'))
            for line in lines:
                self.stdout.write(f'- {line}')
            for failure in failures:
                self.stdout.write(f'- {failure}')
            if options['strict']:
                raise CommandError('Eunoia is not ready for handoff yet.')
            return

        self.stdout.write(self.style.SUCCESS('Readiness check: OK'))
        for line in lines:
            self.stdout.write(f'- {line}')
