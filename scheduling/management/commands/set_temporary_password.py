from django.core.management.base import BaseCommand, CommandError

from scheduling.application.onboarding import reset_temporary_password
from scheduling.models import User, UserRole


class Command(BaseCommand):
    help = 'Assign or reset a temporary password for one or more users.'

    def add_arguments(self, parser):
        parser.add_argument(
            'emails',
            nargs='*',
            help='Email addresses to update.',
        )
        parser.add_argument(
            '--all-students',
            action='store_true',
            help='Apply the temporary password to every student user.',
        )
        parser.add_argument(
            '--password',
            help='Temporary password to assign. Defaults to settings.EUNOIA_DEFAULT_TEMPORARY_PASSWORD.',
        )

    def handle(self, *args, **options):
        emails = options['emails']
        all_students = options['all_students']

        if not emails and not all_students:
            raise CommandError('Provide one or more emails or use --all-students.')

        password = options.get('password')

        queryset = User.objects.none()
        missing_emails = []

        if emails:
            normalized_emails = [User.objects.normalize_email(email) for email in emails]
            queryset = queryset | User.objects.filter(email__in=normalized_emails)
            found_emails = set(queryset.filter(email__in=normalized_emails).values_list('email', flat=True))
            missing_emails = sorted(set(normalized_emails) - found_emails)

        if all_students:
            queryset = queryset | User.objects.filter(role=UserRole.STUDENT)

        users = queryset.distinct().order_by('email')
        if not users.exists():
            raise CommandError('No users matched the provided selection.')

        result = reset_temporary_password(users=users, password=password)

        if missing_emails:
            self.stderr.write(self.style.WARNING(f'Emails not found: {", ".join(missing_emails)}'))

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f'Temporary password assigned to {result.updated_count} users. '
                    'Password change remains required on first login.'
                )
            )
        )
