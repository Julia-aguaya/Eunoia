import os

from django.core.management.base import BaseCommand, CommandError
from scheduling.bootstrap import ensure_demo_slots, ensure_sections, ensure_staff_user, generate_upcoming_sessions


class Command(BaseCommand):
    help = 'Create or update the initial admin user and verify base data.'

    def add_arguments(self, parser):
        parser.add_argument('--admin-email', help='Initial admin email. Falls back to EUNOIA_ADMIN_EMAIL.')
        parser.add_argument('--admin-password', help='Initial admin password. Falls back to EUNOIA_ADMIN_PASSWORD.')
        parser.add_argument('--admin-first-name', default='Admin', help='Initial admin first name.')
        parser.add_argument('--admin-last-name', default='Eunoia', help='Initial admin last name.')
        parser.add_argument(
            '--reset-password',
            action='store_true',
            help='Also reset the password when the admin user already exists.',
        )
        parser.add_argument(
            '--with-demo-slots',
            action='store_true',
            help='Also ensure a small starter weekly schedule for the base sections.',
        )
        parser.add_argument(
            '--generate-next-days',
            type=int,
            default=0,
            help='Generate concrete sessions for the next N days using active weekly slots.',
        )

    def handle(self, *args, **options):
        ensured_sections, created_sections = ensure_sections()
        created_demo_slots = 0
        generated_sessions = 0

        admin_email = options.get('admin_email') or os.getenv('EUNOIA_ADMIN_EMAIL')
        admin_password = options.get('admin_password') or os.getenv('EUNOIA_ADMIN_PASSWORD')
        admin_first_name = options['admin_first_name']
        admin_last_name = options['admin_last_name']
        reset_password = options['reset_password']
        with_demo_slots = options['with_demo_slots']
        generate_next_days = options['generate_next_days']

        if generate_next_days < 0:
            raise CommandError('--generate-next-days must be zero or a positive integer.')

        if not admin_email:
            raise CommandError('Provide --admin-email or set EUNOIA_ADMIN_EMAIL.')
        if not admin_password:
            raise CommandError('Provide --admin-password or set EUNOIA_ADMIN_PASSWORD.')

        admin_result = ensure_staff_user(
            email=admin_email,
            password=admin_password,
            first_name=admin_first_name,
            last_name=admin_last_name,
            reset_password=reset_password,
            is_superuser=True,
        )
        normalized_email = admin_result.user.email
        created_admin = admin_result.created

        if with_demo_slots:
            created_demo_slots = ensure_demo_slots()

        if generate_next_days:
            generated_sessions = generate_upcoming_sessions(generate_next_days)

        action = 'created' if created_admin else 'updated'
        password_status = 'reset' if (created_admin or reset_password) else 'left unchanged'
        extra_bits = []
        if with_demo_slots:
            extra_bits.append(f'demo slots created: {created_demo_slots}')
        if generate_next_days:
            extra_bits.append(f'sessions generated: {generated_sessions}')
        extra_suffix = f"; {'; '.join(extra_bits)}" if extra_bits else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'Bootstrap ready: admin {normalized_email} {action}; '
                f'{ensured_sections} sections ensured ({created_sections} created); '
                f'password {password_status}{extra_suffix}.'
            )
        )
