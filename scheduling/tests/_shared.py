import tempfile
from unittest import mock
from datetime import date, time, timedelta
from io import StringIO
from pathlib import Path

from config.settings import database_config, parse_database_url
from django.core.exceptions import ImproperlyConfigured
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from scheduling.admin import (
    BookingAdminForm,
    HolidayClosureAdmin,
    MonthlyAccessStatusAdmin,
    RecoveryCreditAdmin,
    RecoveryCreditAdminForm,
    UserAdmin,
    UserChangeAdminForm,
    UserCreationAdminForm,
    activate_access_by_payment,
    apply_holiday_closures,
    expire_overdue_recovery_credits,
    reset_temporary_passwords,
    suspend_operational_access,
)
from scheduling.application.onboarding import (
    create_student_onboarding,
    get_default_temporary_password,
    reset_temporary_password,
)
from scheduling.application.recovery_credits import (
    expire_overdue_recovery_credits as expire_overdue_recovery_credits_use_case,
    expire_recovery_credit,
)
from scheduling.demo import DEMO_ADMIN_EMAIL, DEMO_STAFF_EMAIL, DEMO_STUDENT_PASSWORD
from scheduling.models import (
    AuditAction,
    AuditLog,
    Booking,
    BookingSource,
    BookingStatus,
    ClassSession,
    HolidayClosure,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    RecoveryCreditSource,
    RecoveryCreditStatus,
    Section,
    SessionStatus,
    StudentMonthlyPlan,
    StudentMonthlyPlanSlot,
    User,
    WeeklyClassSlot,
    Weekday,
    normalize_month_start,
)
from scheduling.student_import import StudentImportValidationError, import_students_from_csv
from scheduling.use_cases import (
    activate_student_monthly_access,
    apply_holiday_closure,
    cancel_booking,
    create_booking,
    generate_class_sessions,
    grant_manual_recovery_credit,
    mark_booking_attended,
    mark_booking_no_show,
    suspend_student_monthly_access,
    toggle_student_monthly_access,
)
