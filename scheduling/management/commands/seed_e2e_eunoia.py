from datetime import date, time, timedelta
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from scheduling.models import (
    Booking,
    BookingSource,
    ClassSession,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    RecoveryCreditSource,
    RecoveryCreditStatus,
    Section,
    User,
    Weekday,
    WeeklyClassSlot,
)


class Command(BaseCommand):
    help = 'Seed deterministic fake data for isolated E2E runs only.'

    def handle(self, *args, **options):
        if os.getenv('EUNOIA_E2E') != '1' or not settings.DEBUG:
            raise CommandError('E2E seed is disabled outside EUNOIA_E2E with DEBUG=True.')
        db = settings.DATABASES['default']
        if db['ENGINE'] != 'django.db.backends.sqlite3' or Path(db['NAME']).name != 'eunoia-e2e.sqlite3':
            raise CommandError('E2E seed requires the isolated SQLite database.')
        if getattr(settings, 'E2E_FIXED_DATE', None) != '2026-08-10' or timezone.localdate() != date(2026, 8, 10):
            raise CommandError('E2E seed requires the fixed 2026-08-10 America/Argentina/Cordoba clock.')

        base = date(2026, 8, 10)
        password = 'E2E-Only-Password-2026!'
        sections = {
            code: Section.objects.get_or_create(code=code, defaults={'name': name})[0]
            for code, name in (
                ('cadillac', 'Cadillac'),
                ('reformer_arriba', 'Reformer Arriba'),
                ('reformer_abajo', 'Reformer Abajo'),
            )
        }

        def seed_student(key, section_code, *, suspended=False):
            user, _ = User.objects.get_or_create(
                email=f'e2e.{key}@example.test',
                defaults={
                    'first_name': 'E2E',
                    'last_name': key,
                    'primary_section': sections[section_code],
                    'must_change_password': False,
                },
            )
            user.primary_section = sections[section_code]
            user.set_password(password)
            user.is_active = True
            user.must_change_password = False
            user.save()
            MonthlyAccessStatus.objects.update_or_create(
                student=user,
                month=base.replace(day=1),
                defaults={
                    'status': MonthlyAccessStatusType.SUSPENDED if suspended else MonthlyAccessStatusType.ACTIVE,
                    'booking_enabled': not suspended,
                },
            )
            return user

        users = {}
        compatibility = {
            'cadillac': ('cadillac', 'reformer_arriba', 'reformer_abajo'),
            'arriba': ('reformer_arriba', 'reformer_abajo'),
            'abajo': ('reformer_arriba', 'reformer_abajo'),
        }
        origin_sections = {'cadillac': 'cadillac', 'arriba': 'reformer_arriba', 'abajo': 'reformer_abajo'}
        for project in ('desktop', 'mobile'):
            for origin, targets in compatibility.items():
                for target in targets:
                    key = f'{origin}-{target}-{project}'
                    user = seed_student(key, origin_sections[origin])
                    users[key] = user
                    RecoveryCredit.objects.get_or_create(
                        student=user,
                        section=sections[origin_sections[origin]],
                        source=RecoveryCreditSource.TIMELY_CANCELLATION,
                        status=RecoveryCreditStatus.AVAILABLE,
                        defaults={'expires_at': base + timedelta(days=30)},
                    )
            users[f'suspendida-{project}'] = seed_student(f'suspendida-{project}', 'cadillac', suspended=True)
            users[f'capacity-{project}'] = seed_student(f'capacity-{project}', 'cadillac')
            users[f'capacity-filler-{project}'] = seed_student(f'capacity-filler-{project}', 'reformer_arriba')

        staff, _ = User.objects.get_or_create(
            email='e2e.staff@example.test',
            defaults={'first_name': 'E2E', 'last_name': 'Staff', 'is_staff': True, 'role': 'admin', 'must_change_password': False},
        )
        staff.set_password(password)
        staff.is_staff = True
        staff.must_change_password = False
        staff.save()

        for section in sections.values():
            for weekday, offset in ((Weekday.TUESDAY, 1), (Weekday.WEDNESDAY, 2), (Weekday.THURSDAY, 3), (Weekday.FRIDAY, 4)):
                slot, _ = WeeklyClassSlot.objects.get_or_create(
                    section=section,
                    weekday=weekday,
                    start_time=time(9),
                    defaults={'end_time': time(10), 'capacity': 8, 'starts_on': base},
                )
                ClassSession.objects.get_or_create(
                    section=section,
                    date=base + timedelta(days=offset),
                    start_time=time(9),
                    defaults={'slot': slot, 'end_time': time(10), 'capacity': 8},
                )

        for project, start_hour in (('desktop', 12), ('mobile', 13)):
            full_session, _ = ClassSession.objects.get_or_create(
                section=sections['reformer_arriba'],
                date=base + timedelta(days=1),
                start_time=time(start_hour),
                defaults={'end_time': time(start_hour + 1), 'capacity': 1},
            )
            RecoveryCredit.objects.get_or_create(
                student=users[f'capacity-{project}'],
                section=sections['cadillac'],
                source=RecoveryCreditSource.TIMELY_CANCELLATION,
                status=RecoveryCreditStatus.AVAILABLE,
                defaults={'expires_at': base + timedelta(days=30)},
            )
            if not Booking.objects.filter(session=full_session, student=users[f'capacity-filler-{project}']).exists():
                Booking.objects.create_booking(
                    session=full_session,
                    student=users[f'capacity-filler-{project}'],
                    source=BookingSource.MANUAL,
                )

        self.stdout.write(self.style.SUCCESS('E2E seed ready.'))
