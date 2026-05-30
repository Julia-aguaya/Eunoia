from dataclasses import dataclass
from datetime import time, timedelta

from django.contrib.auth import password_validation
from django.utils import timezone

from scheduling.models import Section, User, UserRole, Weekday, WeeklyClassSlot
from scheduling.use_cases import generate_class_sessions


DEFAULT_SECTIONS = [
    ('reformer_arriba', 'Reformer Arriba'),
    ('reformer_abajo', 'Reformer Abajo'),
    ('cadillac', 'Cadillac'),
]

DEFAULT_DEMO_SLOTS = [
    ('reformer_arriba', Weekday.MONDAY, time(8, 0), time(9, 0)),
    ('reformer_arriba', Weekday.WEDNESDAY, time(18, 0), time(19, 0)),
    ('reformer_abajo', Weekday.TUESDAY, time(9, 0), time(10, 0)),
    ('reformer_abajo', Weekday.THURSDAY, time(17, 0), time(18, 0)),
    ('cadillac', Weekday.MONDAY, time(10, 0), time(11, 0)),
    ('cadillac', Weekday.FRIDAY, time(16, 0), time(17, 0)),
]


@dataclass(frozen=True)
class StaffBootstrapResult:
    user: User
    created: bool
    password_reset: bool


def ensure_sections():
    ensured = 0
    created = 0

    for code, name in DEFAULT_SECTIONS:
        _, was_created = Section.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'default_capacity': 7,
                'is_active': True,
            },
        )
        ensured += 1
        if was_created:
            created += 1

    return ensured, created


def ensure_staff_user(
    *,
    email,
    password,
    first_name,
    last_name,
    reset_password=False,
    is_superuser=False,
):
    password_validation.validate_password(password)

    normalized_email = User.objects.normalize_email(email)
    user = User.objects.filter(email=normalized_email).first()
    created = user is None
    password_reset = created or reset_password

    if created:
        user = User(
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.ADMIN,
            is_staff=True,
            is_superuser=is_superuser,
            is_active=True,
            must_change_password=False,
        )
        user.set_initial_password(password, require_password_change=False)
        user.save()
        return StaffBootstrapResult(user=user, created=True, password_reset=True)

    changed_fields = []
    if user.first_name != first_name:
        user.first_name = first_name
        changed_fields.append('first_name')
    if user.last_name != last_name:
        user.last_name = last_name
        changed_fields.append('last_name')
    if user.role != UserRole.ADMIN:
        user.role = UserRole.ADMIN
        changed_fields.append('role')
    if not user.is_staff:
        user.is_staff = True
        changed_fields.append('is_staff')
    if user.is_superuser != is_superuser:
        user.is_superuser = is_superuser
        changed_fields.append('is_superuser')
    if not user.is_active:
        user.is_active = True
        changed_fields.append('is_active')
    if user.must_change_password:
        user.must_change_password = False
        user.temporary_password_set_at = None
        changed_fields.extend(['must_change_password', 'temporary_password_set_at'])
    if reset_password:
        user.set_initial_password(password, require_password_change=False)
        changed_fields.extend(['password', 'must_change_password', 'temporary_password_set_at'])

    if changed_fields:
        user.save(update_fields=sorted(set(changed_fields + ['updated_at'])))

    return StaffBootstrapResult(user=user, created=False, password_reset=password_reset)


def ensure_demo_slots(*, notes='Starter schedule created by bootstrap_eunoia.'):
    sections_by_code = {section.code: section for section in Section.objects.all()}
    created = 0

    for section_code, weekday, start_time, end_time in DEFAULT_DEMO_SLOTS:
        section = sections_by_code[section_code]
        _, was_created = WeeklyClassSlot.objects.update_or_create(
            section=section,
            weekday=weekday,
            start_time=start_time,
            defaults={
                'end_time': end_time,
                'capacity': None,
                'is_active': True,
                'notes': notes,
            },
        )
        if was_created:
            created += 1

    return created


def generate_upcoming_sessions(next_days):
    start_date = timezone.localdate()
    end_date = start_date + timedelta(days=max(next_days - 1, 0))
    result = generate_class_sessions(start_date=start_date, end_date=end_date)
    return result.created_count
