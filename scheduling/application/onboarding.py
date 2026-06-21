from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import password_validation
from django.db import transaction
from django.utils import timezone

from ..models import MonthlyAccessStatus, MonthlyAccessStatusType, User, UserRole, normalize_month_start


@dataclass(frozen=True)
class ResetTemporaryPasswordResult:
    updated_count: int


def get_default_temporary_password():
    return settings.EUNOIA_DEFAULT_TEMPORARY_PASSWORD


def resolve_temporary_password(password=None):
    temporary_password = password or get_default_temporary_password()
    password_validation.validate_password(temporary_password)
    return temporary_password


def create_student_onboarding(
    *,
    email,
    first_name,
    last_name,
    primary_section=None,
    phone='',
    notes='',
    role=UserRole.STUDENT,
    temporary_password=None,
    must_change_password=True,
    is_active=True,
    is_staff=False,
    is_superuser=False,
    groups=(),
    user_permissions=(),
):
    user = User(
        email=User.objects.normalize_email(email),
        first_name=first_name,
        last_name=last_name,
        primary_section=primary_section,
        phone=phone,
        notes=notes,
        role=role,
        is_active=is_active,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    user.set_initial_password(
        resolve_temporary_password(temporary_password),
        require_password_change=must_change_password,
    )

    with transaction.atomic():
        user.save()
        user.groups.set(groups)
        user.user_permissions.set(user_permissions)

    return user


def reset_temporary_password(*, users, password=None):
    temporary_password = resolve_temporary_password(password)

    updated_count = 0
    with transaction.atomic():
        for user in users:
            user.set_temporary_password(temporary_password)
            user.save(update_fields=['password', 'must_change_password', 'temporary_password_set_at', 'updated_at'])
            updated_count += 1

    return ResetTemporaryPasswordResult(updated_count=updated_count)


def create_student_self_signup(*, email, first_name, last_name, primary_section, phone='', password):
    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            primary_section=primary_section,
            phone=phone,
            role=UserRole.STUDENT,
            must_change_password=False,
            is_active=True,
            is_staff=False,
        )
        MonthlyAccessStatus.objects.get_or_create(
            student=user,
            month=normalize_month_start(timezone.localdate()),
            defaults={
                'status': MonthlyAccessStatusType.PENDING_PAYMENT,
                'booking_enabled': False,
            },
        )

    return user
