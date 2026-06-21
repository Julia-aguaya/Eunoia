import calendar
from datetime import datetime, timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


def normalize_month_start(value):
    return value.replace(day=1)


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserRole(models.TextChoices):
    STUDENT = 'student', 'Student'
    ADMIN = 'admin', 'Admin'


class ActivityType(models.TextChoices):
    REFORMER_UPSTAIRS = 'reformer_arriba', 'Reformer Arriba'
    REFORMER_DOWNSTAIRS = 'reformer_abajo', 'Reformer Abajo'
    CADILLAC = 'cadillac', 'Cadillac'


class BookingStatus(models.TextChoices):
    BOOKED = 'booked', 'Booked'
    CANCELLED = 'cancelled', 'Cancelled'
    ATTENDED = 'attended', 'Attended'
    NO_SHOW = 'no_show', 'No Show'
    MOVED = 'moved', 'Moved'


class BookingSource(models.TextChoices):
    FIXED_SLOT = 'fixed_slot', 'Fixed Slot'
    MAKEUP = 'makeup', 'Makeup'
    MANUAL = 'manual', 'Manual'


class SessionStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Scheduled'
    CANCELLED = 'cancelled', 'Cancelled'
    HOLIDAY_CLOSED = 'holiday_closed', 'Holiday Closed'


class RecoveryCreditStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    USED = 'used', 'Used'
    EXPIRED = 'expired', 'Expired'
    REVOKED = 'revoked', 'Revoked'


class RecoveryCreditSource(models.TextChoices):
    TIMELY_CANCELLATION = 'timely_cancellation', 'Timely Cancellation'
    HOLIDAY_CLOSURE = 'holiday_closure', 'Holiday Closure'
    MANUAL = 'manual', 'Manual'


class MonthlyAccessStatusType(models.TextChoices):
    PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'


class AuditAction(models.TextChoices):
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'
    STATUS_CHANGE = 'status_change', 'Status Change'
    MOVE = 'move', 'Move'
    CREDIT = 'credit', 'Credit'


class Weekday(models.IntegerChoices):
    MONDAY = 1, 'Monday'
    TUESDAY = 2, 'Tuesday'
    WEDNESDAY = 3, 'Wednesday'
    THURSDAY = 4, 'Thursday'
    FRIDAY = 5, 'Friday'
    SATURDAY = 6, 'Saturday'
    SUNDAY = 7, 'Sunday'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('must_change_password', False)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STUDENT)
    primary_section = models.ForeignKey(
        'Section',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='primary_students',
    )
    phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    must_change_password = models.BooleanField(default=True)
    temporary_password_set_at = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['last_name', 'first_name', 'email']

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_monthly_access_for(self, target_date):
        return self.monthly_access_statuses.filter(month=normalize_month_start(target_date)).first()

    def set_initial_password(self, raw_password, *, require_password_change=True):
        self.set_password(raw_password)
        self.must_change_password = require_password_change
        self.temporary_password_set_at = timezone.now() if require_password_change else None
        return self

    def set_temporary_password(self, raw_password):
        return self.set_initial_password(raw_password, require_password_change=True)

    def has_operational_booking_access_for(self, target_date):
        access = self.get_monthly_access_for(target_date)
        if access is None:
            return False
        return access.grants_operational_booking_access()

    def save(self, *args, **kwargs):
        if self.must_change_password and self.temporary_password_set_at is None:
            self.temporary_password_set_at = timezone.now()
        elif not self.must_change_password:
            self.temporary_password_set_at = None
        super().save(*args, **kwargs)


class Section(TimeStampedModel):
    code = models.CharField(max_length=32, choices=ActivityType.choices, unique=True)
    name = models.CharField(max_length=120)
    default_capacity = models.PositiveSmallIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class WeeklyClassSlot(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name='weekly_slots')
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['weekday', 'start_time', 'section__name']
        constraints = [
            models.UniqueConstraint(
                fields=['section', 'weekday', 'start_time'],
                name='unique_weekly_slot_per_section',
            ),
        ]

    def __str__(self):
        return f'{self.section} - {self.get_weekday_display()} {self.start_time:%H:%M}'

    def is_effective_on(self, target_date):
        if not self.is_active:
            return False
        if target_date.isoweekday() != self.weekday:
            return False
        if self.starts_on and target_date < self.starts_on:
            return False
        if self.ends_on and target_date > self.ends_on:
            return False
        return True

    def build_session_for_date(self, target_date, holiday_closure=None):
        if not self.is_effective_on(target_date):
            raise ValueError('Weekly slot is not effective on the requested date.')

        return ClassSession(
            slot=self,
            section=self.section,
            date=target_date,
            start_time=self.start_time,
            end_time=self.end_time,
            capacity=self.capacity or self.section.default_capacity,
            status=(
                SessionStatus.HOLIDAY_CLOSED
                if holiday_closure is not None
                else SessionStatus.SCHEDULED
            ),
            holiday_closure=holiday_closure,
        )


class HolidayClosure(TimeStampedModel):
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_holiday_closures',
    )
    recovery_credits_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.date} - {self.reason}'

    def apply(self, *, actor=None):
        with transaction.atomic():
            closure = HolidayClosure.objects.select_for_update().get(pk=self.pk)
            updated_sessions = ClassSession.objects.filter(date=closure.date).exclude(
                status=SessionStatus.HOLIDAY_CLOSED,
                holiday_closure_id=closure.pk,
            ).update(
                status=SessionStatus.HOLIDAY_CLOSED,
                holiday_closure=closure,
                updated_at=timezone.now(),
            )

            created_credits = 0
            existing_credits = 0
            affected_bookings = (
                Booking.objects.select_related('student', 'session', 'session__section')
                .filter(session__date=closure.date, status__in=Booking.active_statuses())
                .order_by('pk')
            )
            for booking in affected_bookings:
                _, created = RecoveryCredit.objects.grant_holiday_closure_credit(
                    booking=booking,
                    granted_by=actor,
                    notes=f'Holiday closure on {closure.date}: {closure.reason}',
                )
                if created:
                    created_credits += 1
                else:
                    existing_credits += 1

            if not closure.recovery_credits_processed:
                closure.recovery_credits_processed = True
                closure.save(update_fields=['recovery_credits_processed', 'updated_at'])

            self.recovery_credits_processed = closure.recovery_credits_processed
            return {
                'updated_sessions': updated_sessions,
                'created_credits': created_credits,
                'existing_credits': existing_credits,
            }


class ClassSession(TimeStampedModel):
    slot = models.ForeignKey(
        WeeklyClassSlot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sessions',
    )
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name='sessions')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.SCHEDULED)
    holiday_closure = models.ForeignKey(
        HolidayClosure,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sessions',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['date', 'start_time', 'section__name']
        constraints = [
            models.UniqueConstraint(
                fields=['section', 'date', 'start_time'],
                name='unique_session_per_section_datetime',
            ),
        ]

    def __str__(self):
        return f'{self.section} - {self.date} {self.start_time:%H:%M}'

    def active_bookings(self):
        return self.bookings.filter(status__in=Booking.active_statuses())

    def starts_at(self):
        return timezone.make_aware(datetime.combine(self.date, self.start_time))

    def ends_at(self):
        return timezone.make_aware(datetime.combine(self.date, self.end_time))


class RecoveryCreditManager(models.Manager):
    def grant_manual_credit(self, *, student, section, granted_by=None, reference_date=None, notes=''):
        credit = self.model(
            student=student,
            section=section,
            source=RecoveryCreditSource.MANUAL,
            status=RecoveryCreditStatus.AVAILABLE,
            granted_by=granted_by,
            notes=notes,
            expires_at=timezone.localdate(),
        )
        credit.set_expiration_date(reference_date=reference_date)
        credit.save(force_insert=True)
        return credit

    def grant_holiday_closure_credit(self, *, booking, granted_by=None, notes=''):
        return self.get_or_create(
            student=booking.student,
            section=booking.session.section,
            source=RecoveryCreditSource.HOLIDAY_CLOSURE,
            origin_session=booking.session,
            defaults={
                'status': RecoveryCreditStatus.AVAILABLE,
                'granted_by': granted_by,
                'expires_at': add_months(booking.session.date, 3),
                'notes': notes,
            },
        )


class RecoveryCredit(TimeStampedModel):
    SECTION_COMPATIBILITY = {
        ActivityType.CADILLAC: frozenset({
            ActivityType.CADILLAC,
            ActivityType.REFORMER_UPSTAIRS,
            ActivityType.REFORMER_DOWNSTAIRS,
        }),
        ActivityType.REFORMER_UPSTAIRS: frozenset({ActivityType.REFORMER_UPSTAIRS}),
        ActivityType.REFORMER_DOWNSTAIRS: frozenset({ActivityType.REFORMER_DOWNSTAIRS}),
    }
    STATUS_TRANSITIONS = {
        RecoveryCreditStatus.AVAILABLE: frozenset({
            RecoveryCreditStatus.USED,
            RecoveryCreditStatus.EXPIRED,
            RecoveryCreditStatus.REVOKED,
        }),
        RecoveryCreditStatus.USED: frozenset(),
        RecoveryCreditStatus.EXPIRED: frozenset(),
        RecoveryCreditStatus.REVOKED: frozenset(),
    }
    objects = RecoveryCreditManager()

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recovery_credits')
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name='recovery_credits')
    source = models.CharField(max_length=30, choices=RecoveryCreditSource.choices)
    status = models.CharField(
        max_length=20,
        choices=RecoveryCreditStatus.choices,
        default=RecoveryCreditStatus.AVAILABLE,
    )
    origin_session = models.ForeignKey(
        ClassSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='generated_recovery_credits',
    )
    granted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='granted_recovery_credits',
    )
    expires_at = models.DateField()
    used_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['status', 'expires_at']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'origin_session', 'source'],
                condition=Q(source=RecoveryCreditSource.HOLIDAY_CLOSURE),
                name='unique_holiday_closure_credit_per_student_session',
            ),
        ]

    def __str__(self):
        return f'{self.student} - {self.section} - {self.status}'

    @classmethod
    def allowed_transitions_from(cls, status):
        return cls.STATUS_TRANSITIONS.get(status, frozenset())

    def available_status_transitions(self):
        return self.allowed_transitions_from(self.status)

    def can_transition_to(self, target_status):
        return target_status == self.status or target_status in self.available_status_transitions()

    def _stored_status(self):
        if self.pk is None:
            return None

        return type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()

    def validate_status_transition(self, target_status, *, previous_status=None):
        current_status = self.status if previous_status is None else previous_status

        if current_status is None or current_status == target_status:
            return

        if target_status not in self.allowed_transitions_from(current_status):
            allowed_targets = sorted(self.allowed_transitions_from(current_status))
            allowed_targets_label = ', '.join(allowed_targets) or 'none'
            raise ValidationError({
                'status': (
                    f'Invalid recovery credit transition from {current_status} to {target_status}. '
                    f'Allowed targets: {allowed_targets_label}.'
                )
            })

    def calculate_expiration_date(self, reference_date=None):
        base_date = reference_date or getattr(self.origin_session, 'date', None) or timezone.localdate()
        return add_months(base_date, 3)

    def set_expiration_date(self, reference_date=None):
        self.expires_at = self.calculate_expiration_date(reference_date=reference_date)
        return self.expires_at

    def is_overdue(self, on_date=None):
        reference_date = on_date or timezone.localdate()
        return self.expires_at < reference_date

    def is_available(self, on_date=None):
        return self.status == RecoveryCreditStatus.AVAILABLE and not self.is_overdue(on_date=on_date)

    def is_expired(self, on_date=None):
        return self.status == RecoveryCreditStatus.EXPIRED or (
            self.status == RecoveryCreditStatus.AVAILABLE and self.is_overdue(on_date=on_date)
        )

    def clean(self):
        super().clean()

        errors = {}

        def add_error(field, message):
            errors.setdefault(field, []).append(message)

        previous_status = self._stored_status()
        if previous_status is not None:
            try:
                self.validate_status_transition(self.status, previous_status=previous_status)
            except ValidationError as exc:
                for field, messages in exc.message_dict.items():
                    for message in messages:
                        add_error(field, message)

        if self.status == RecoveryCreditStatus.USED:
            if self.used_at is None:
                add_error('used_at', 'Used recovery credits must keep the usage timestamp.')
        elif self.used_at is not None:
            add_error('used_at', 'Only used recovery credits can keep a usage timestamp.')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def expire_if_needed(self, on_date=None):
        if self.status != RecoveryCreditStatus.AVAILABLE:
            return False

        if not self.is_overdue(on_date=on_date):
            return False

        self.validate_status_transition(RecoveryCreditStatus.EXPIRED)
        self.status = RecoveryCreditStatus.EXPIRED
        return True

    def expire_manually(self, on_date=None):
        reference_date = on_date or timezone.localdate()

        if self.status == RecoveryCreditStatus.EXPIRED:
            return False

        if self.status != RecoveryCreditStatus.AVAILABLE:
            raise ValidationError('Only available recovery credits can be manually expired.')

        self.validate_status_transition(RecoveryCreditStatus.EXPIRED)
        self.status = RecoveryCreditStatus.EXPIRED
        if self.expires_at > reference_date:
            self.expires_at = reference_date
        return True

    def validate_usage_for(self, *, student, session, on_date=None):
        errors = {}

        if self.student_id != student.pk:
            errors.setdefault('used_recovery_credit', []).append('Recovery credit belongs to another student.')

        if not self.is_session_compatible(session):
            errors.setdefault('used_recovery_credit', []).append(
                'Recovery credit is not compatible with this section.'
            )

        if self.origin_session_id == session.pk:
            errors.setdefault('used_recovery_credit', []).append(
                'Recovery credit must be used for another session in the same section.'
            )

        if self.is_expired(on_date=on_date):
            errors.setdefault('used_recovery_credit', []).append('Recovery credit is expired.')
        elif self.status != RecoveryCreditStatus.AVAILABLE:
            errors.setdefault('used_recovery_credit', []).append('Recovery credit is not available.')

        if errors:
            raise ValidationError(errors)

    def mark_as_used(self, *, student, session, when=None):
        usage_time = when or timezone.now()
        self.validate_usage_for(student=student, session=session, on_date=usage_time.date())
        self.validate_status_transition(RecoveryCreditStatus.USED)
        self.status = RecoveryCreditStatus.USED
        self.used_at = usage_time

    def compatible_section_codes(self):
        return self.SECTION_COMPATIBILITY.get(self.section.code, frozenset({self.section.code}))

    def is_session_compatible(self, session):
        return session.section.code in self.compatible_section_codes()


class BookingManager(models.Manager):
    def create_booking(self, *, session, student, source=BookingSource.FIXED_SLOT, **extra_fields):
        with transaction.atomic():
            locked_session = ClassSession.objects.select_for_update().select_related('section').get(pk=session.pk)
            recovery_credit = extra_fields.pop('used_recovery_credit', None)
            locked_credit = None
            if recovery_credit is not None:
                locked_credit = RecoveryCredit.objects.select_for_update().get(pk=recovery_credit.pk)
                if source == BookingSource.FIXED_SLOT:
                    source = BookingSource.MAKEUP
            booking = self.model(
                session=locked_session,
                student=student,
                status=BookingStatus.BOOKED,
                source=source,
                used_recovery_credit=locked_credit,
                **extra_fields,
            )
            booking.save(force_insert=True)
            if locked_credit is not None:
                locked_credit.mark_as_used(student=student, session=locked_session)
                locked_credit.save(update_fields=['status', 'used_at', 'updated_at'])
            return booking


class Booking(TimeStampedModel):
    ACTIVE_STATUSES = (BookingStatus.BOOKED,)
    STATUS_TRANSITIONS = {
        BookingStatus.BOOKED: frozenset({
            BookingStatus.CANCELLED,
            BookingStatus.ATTENDED,
            BookingStatus.NO_SHOW,
            BookingStatus.MOVED,
        }),
        BookingStatus.CANCELLED: frozenset(),
        BookingStatus.ATTENDED: frozenset(),
        BookingStatus.NO_SHOW: frozenset(),
        BookingStatus.MOVED: frozenset(),
    }
    SELF_SERVICE_CANCELLATION_WINDOW = timedelta(hours=2)
    objects = BookingManager()

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='bookings')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.BOOKED)
    source = models.CharField(max_length=20, choices=BookingSource.choices, default=BookingSource.FIXED_SLOT)
    used_recovery_credit = models.ForeignKey(
        RecoveryCredit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bookings',
    )
    moved_from_booking = models.OneToOneField(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='moved_to_booking',
    )
    moved_to_session = models.ForeignKey(
        ClassSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='incoming_moves',
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cancelled_bookings',
    )
    cancellation_generates_recovery = models.BooleanField(default=False)
    attendance_marked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['session__date', 'session__start_time', 'student__last_name']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                condition=Q(status=BookingStatus.BOOKED),
                name='unique_active_booking_per_student_session',
            ),
        ]

    def __str__(self):
        return f'{self.student} - {self.session}'

    @classmethod
    def active_statuses(cls):
        return cls.ACTIVE_STATUSES

    def is_active_reservation(self):
        return self.status in self.active_statuses()

    @classmethod
    def allowed_transitions_from(cls, status):
        return cls.STATUS_TRANSITIONS.get(status, frozenset())

    def available_status_transitions(self):
        return self.allowed_transitions_from(self.status)

    def can_transition_to(self, target_status):
        return target_status == self.status or target_status in self.available_status_transitions()

    def _stored_status(self):
        if self.pk is None:
            return None

        return type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()

    def validate_status_transition(self, target_status, *, previous_status=None):
        current_status = self.status if previous_status is None else previous_status

        if current_status is None or current_status == target_status:
            return

        if target_status not in self.allowed_transitions_from(current_status):
            allowed_targets = sorted(self.allowed_transitions_from(current_status))
            allowed_targets_label = ', '.join(allowed_targets) or 'none'
            raise ValidationError({
                'status': (
                    f'Invalid booking transition from {current_status} to {target_status}. '
                    f'Allowed targets: {allowed_targets_label}.'
                )
            })

    def _transition_to(self, target_status, *, update_fields, previous_status=None):
        self.validate_status_transition(target_status, previous_status=previous_status)
        self.status = target_status
        self.save(update_fields=update_fields)
        return self

    def clean(self):
        super().clean()

        errors = {}

        def add_error(field, message):
            errors.setdefault(field, []).append(message)

        previous_status = self._stored_status()
        if previous_status is not None:
            try:
                self.validate_status_transition(self.status, previous_status=previous_status)
            except ValidationError as exc:
                for field, messages in exc.message_dict.items():
                    for message in messages:
                        add_error(field, message)

        if self.moved_from_booking_id is not None and self.moved_from_booking_id == self.pk:
            add_error('moved_from_booking', 'A moved booking cannot reference itself as origin.')

        if self.status == BookingStatus.MOVED:
            if self.moved_to_session_id is None:
                add_error('moved_to_session', 'Moved bookings must keep the destination session.')
            elif self.session_id is not None and self.moved_to_session_id == self.session_id:
                add_error('moved_to_session', 'A moved booking must keep a different destination session.')
        elif self.moved_to_session_id is not None:
            add_error('moved_to_session', 'Only moved bookings can keep a destination session reference.')

        if self.status in {BookingStatus.ATTENDED, BookingStatus.NO_SHOW}:
            if self.attendance_marked_at is None:
                add_error('attendance_marked_at', 'Attendance-marked bookings must keep the mark timestamp.')
        elif self.attendance_marked_at is not None:
            add_error('attendance_marked_at', 'Only attended or no-show bookings can keep an attendance timestamp.')

        if self.status != BookingStatus.CANCELLED:
            if self.cancelled_at is not None:
                add_error('cancelled_at', 'Only cancelled bookings can keep a cancellation timestamp.')
            if self.cancelled_by_id is not None:
                add_error('cancelled_by', 'Only cancelled bookings can keep a cancellation actor.')
            if self.cancellation_generates_recovery:
                add_error('cancellation_generates_recovery', 'Only cancelled bookings can generate recovery credits.')

        if self.moved_from_booking_id is not None:
            original_booking = self.moved_from_booking
            if self.student_id is not None and original_booking.student_id != self.student_id:
                add_error('moved_from_booking', 'Moved bookings must belong to the same student as the original booking.')
            if self.session_id is not None and original_booking.session_id == self.session_id:
                add_error('session', 'A booking can only be moved to a different session.')

        if errors:
            raise ValidationError(errors)

        if self.session_id is None or self.student_id is None or not self.is_active_reservation():
            return

        student = self.student
        session = self.session

        if student.primary_section_id is None:
            add_error('student', 'Student must have a primary section before reserving.')
        elif student.primary_section_id != session.section_id:
            add_error('student', 'Student can only reserve sessions in their primary section.')

        if not student.has_operational_booking_access_for(session.date):
            add_error('student', 'Student must have active monthly operational access for this session month.')

        if session.status in {SessionStatus.CANCELLED, SessionStatus.HOLIDAY_CLOSED}:
            add_error('session', 'This session is closed and cannot be booked.')

        active_bookings = session.active_bookings().exclude(pk=self.pk)
        if active_bookings.count() >= session.capacity:
            add_error('session', 'This session has reached its capacity.')

        duplicate_exists = active_bookings.filter(student_id=self.student_id).exists()
        if duplicate_exists:
            add_error('student', 'Student already has an active booking for this session.')

        if self.used_recovery_credit_id is not None:
            reuses_original_recovery_credit = (
                self.moved_from_booking_id is not None
                and self.moved_from_booking.student_id == student.pk
                and self.moved_from_booking.used_recovery_credit_id == self.used_recovery_credit_id
            )

            if not reuses_original_recovery_credit:
                try:
                    self.used_recovery_credit.validate_usage_for(
                        student=student,
                        session=session,
                        on_date=timezone.localdate(),
                    )
                except ValidationError as exc:
                    for field, messages in exc.message_dict.items():
                        for message in messages:
                            add_error(field, message)

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def remaining_time_until_start(self, when=None):
        reference_time = when or timezone.now()
        return self.session.starts_at() - reference_time

    def _mark_attendance_status(self, *, status, when=None):
        event_time = when or timezone.now()

        if status not in {BookingStatus.ATTENDED, BookingStatus.NO_SHOW}:
            raise ValueError('Unsupported attendance status.')

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related('session', 'session__holiday_closure')
                .get(pk=self.pk)
            )

            if booking.status != BookingStatus.BOOKED:
                raise ValidationError('Only active bookings can be marked for attendance.')

            if booking.session.status != SessionStatus.SCHEDULED:
                raise ValidationError('Only scheduled sessions can have attendance marked.')

            if event_time < booking.session.starts_at():
                raise ValidationError('Attendance cannot be marked before the class starts.')

            if status == BookingStatus.NO_SHOW and event_time < booking.session.ends_at():
                raise ValidationError('A no-show can only be marked after the class ends.')

            booking.attendance_marked_at = event_time
            return booking._transition_to(
                status,
                update_fields=['status', 'attendance_marked_at', 'updated_at'],
                previous_status=booking.status,
            )

    def mark_attended(self, *, when=None):
        return self._mark_attendance_status(status=BookingStatus.ATTENDED, when=when)

    def mark_no_show(self, *, when=None):
        return self._mark_attendance_status(status=BookingStatus.NO_SHOW, when=when)

    def move_to_session(self, *, target_session, actor=None, when=None):
        move_time = when or timezone.now()

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related('student', 'session', 'session__section', 'used_recovery_credit')
                .get(pk=self.pk)
            )
            locked_target_session = ClassSession.objects.select_for_update().select_related('section').get(pk=target_session.pk)

            if not booking.is_active_reservation():
                raise ValidationError('Only active bookings can be moved.')

            if booking.session_id == locked_target_session.pk:
                raise ValidationError('A booking can only be moved to a different session.')

            if Booking.objects.filter(moved_from_booking=booking).exists():
                raise ValidationError('This booking was already moved to another session.')

            new_booking = Booking(
                session=locked_target_session,
                student=booking.student,
                status=BookingStatus.BOOKED,
                source=booking.source,
                used_recovery_credit=booking.used_recovery_credit,
                moved_from_booking=booking,
                notes=booking.notes,
            )
            new_booking.save(force_insert=True)

            booking.moved_to_session = locked_target_session
            booking._transition_to(
                BookingStatus.MOVED,
                update_fields=['status', 'moved_to_session', 'updated_at'],
                previous_status=booking.status,
            )

            AuditLog.objects.create(
                actor=actor,
                action=AuditAction.MOVE,
                entity_type='Booking',
                entity_id=booking.pk,
                description=(
                    f'Moved booking for {booking.student.get_full_name() or booking.student.email} '
                    f'from session #{booking.session_id} to session #{locked_target_session.pk}'
                ),
                payload={
                    'student_id': booking.student_id,
                    'from_booking_id': booking.pk,
                    'to_booking_id': new_booking.pk,
                    'from_session_id': booking.session_id,
                    'to_session_id': locked_target_session.pk,
                    'source': booking.source,
                    'used_recovery_credit_id': booking.used_recovery_credit_id,
                    'moved_at': move_time.isoformat(),
                },
            )

            return new_booking

    def cancel_by_student(self, *, actor=None, when=None):
        cancellation_time = when or timezone.now()
        acting_user = actor or self.student

        if acting_user.pk != self.student_id:
            raise ValidationError('Only the booking student can cancel this booking.')

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related('session', 'session__section', 'student')
                .get(pk=self.pk)
            )

            if not booking.is_active_reservation():
                raise ValidationError('Only active bookings can be cancelled.')

            if booking.remaining_time_until_start(when=cancellation_time) <= self.SELF_SERVICE_CANCELLATION_WINDOW:
                raise ValidationError('Self-service cancellation is only allowed more than 2 hours before class start.')

            booking.cancelled_at = cancellation_time
            booking.cancelled_by = acting_user
            booking.cancellation_generates_recovery = True
            booking._transition_to(
                BookingStatus.CANCELLED,
                update_fields=[
                    'status',
                    'cancelled_at',
                    'cancelled_by',
                    'cancellation_generates_recovery',
                    'updated_at',
                ],
                previous_status=booking.status,
            )

            recovery_credit = RecoveryCredit(
                student=booking.student,
                section=booking.session.section,
                source=RecoveryCreditSource.TIMELY_CANCELLATION,
                status=RecoveryCreditStatus.AVAILABLE,
                origin_session=booking.session,
                expires_at=booking.session.date,
            )
            recovery_credit.set_expiration_date(reference_date=booking.session.date)
            recovery_credit.save(force_insert=True)

            return recovery_credit


class MonthlyAccessStatus(TimeStampedModel):
    STATUS_TRANSITIONS = {
        MonthlyAccessStatusType.PENDING_PAYMENT: frozenset({
            MonthlyAccessStatusType.ACTIVE,
            MonthlyAccessStatusType.SUSPENDED,
        }),
        MonthlyAccessStatusType.ACTIVE: frozenset({
            MonthlyAccessStatusType.PENDING_PAYMENT,
            MonthlyAccessStatusType.SUSPENDED,
        }),
        MonthlyAccessStatusType.SUSPENDED: frozenset({
            MonthlyAccessStatusType.ACTIVE,
        }),
    }
    STATUS_UPDATE_FIELDS = {
        MonthlyAccessStatusType.PENDING_PAYMENT: (
            'status',
            'booking_enabled',
            'activated_at',
            'deactivated_at',
            'activated_by',
            'updated_at',
        ),
        MonthlyAccessStatusType.ACTIVE: (
            'status',
            'booking_enabled',
            'activated_at',
            'deactivated_at',
            'activated_by',
            'updated_at',
        ),
        MonthlyAccessStatusType.SUSPENDED: (
            'status',
            'booking_enabled',
            'deactivated_at',
            'updated_at',
        ),
    }

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_access_statuses')
    month = models.DateField(help_text='Use the first day of the month.')
    status = models.CharField(
        max_length=20,
        choices=MonthlyAccessStatusType.choices,
        default=MonthlyAccessStatusType.PENDING_PAYMENT,
    )
    booking_enabled = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activated_access_statuses',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-month', 'student__last_name']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'month'],
                name='unique_monthly_access_status_per_student',
            ),
        ]

    def __str__(self):
        return f'{self.student} - {self.month:%Y-%m} - {self.status}'

    @classmethod
    def allowed_transitions_from(cls, status):
        return cls.STATUS_TRANSITIONS.get(status, frozenset())

    def available_status_transitions(self):
        return self.allowed_transitions_from(self.status)

    def can_transition_to(self, target_status):
        return target_status == self.status or target_status in self.available_status_transitions()

    def _stored_status(self):
        if self.pk is None:
            return None

        return type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()

    def validate_status_transition(self, target_status, *, previous_status=None):
        current_status = self.status if previous_status is None else previous_status

        if current_status is None or current_status == target_status:
            return

        if target_status not in self.allowed_transitions_from(current_status):
            allowed_targets = sorted(self.allowed_transitions_from(current_status))
            allowed_targets_label = ', '.join(allowed_targets) or 'none'
            raise ValidationError({
                'status': (
                    f'Invalid monthly access transition from {current_status} to {target_status}. '
                    f'Allowed targets: {allowed_targets_label}.'
                )
            })

    def grants_operational_booking_access(self):
        return self.status == MonthlyAccessStatusType.ACTIVE and self.booking_enabled

    @classmethod
    def transition_update_fields(cls, target_status):
        return cls.STATUS_UPDATE_FIELDS.get(target_status, ('status', 'updated_at'))

    def _status_transition_updates(self, target_status, *, actor=None, when=None):
        event_time = when or timezone.now()

        if target_status == MonthlyAccessStatusType.PENDING_PAYMENT:
            return {
                'status': MonthlyAccessStatusType.PENDING_PAYMENT,
                'booking_enabled': False,
                'activated_at': None,
                'deactivated_at': None,
                'activated_by': None,
            }

        if target_status == MonthlyAccessStatusType.ACTIVE:
            updates = {
                'status': MonthlyAccessStatusType.ACTIVE,
                'booking_enabled': True,
                'activated_at': event_time,
                'deactivated_at': None,
            }
            if actor is not None:
                updates['activated_by'] = actor
            return updates

        if target_status == MonthlyAccessStatusType.SUSPENDED:
            return {
                'status': MonthlyAccessStatusType.SUSPENDED,
                'booking_enabled': False,
                'deactivated_at': event_time,
            }

        raise ValueError(f'Unsupported monthly access target status: {target_status}.')

    def _transition_to(self, target_status, *, actor=None, when=None, previous_status=None):
        current_status = self.status if previous_status is None else previous_status
        self.validate_status_transition(target_status, previous_status=current_status)

        if current_status == target_status:
            return self

        for field_name, value in self._status_transition_updates(target_status, actor=actor, when=when).items():
            setattr(self, field_name, value)

        return self

    def _persist_transition_to(self, target_status, *, actor=None, when=None, previous_status=None):
        current_status = self.status if previous_status is None else previous_status
        self._transition_to(target_status, actor=actor, when=when, previous_status=current_status)

        if current_status == target_status:
            return self

        if self.pk is None:
            self.save()
            return self

        self.save(update_fields=self.transition_update_fields(target_status))
        return self

    def mark_pending_payment(self):
        return self._persist_transition_to(MonthlyAccessStatusType.PENDING_PAYMENT)

    def activate_by_payment(self, actor=None, when=None):
        return self._persist_transition_to(MonthlyAccessStatusType.ACTIVE, actor=actor, when=when)

    def suspend_operational_access(self, when=None):
        return self._persist_transition_to(MonthlyAccessStatusType.SUSPENDED, when=when)

    def clean(self):
        super().clean()

        errors = {}

        def add_error(field, message):
            errors.setdefault(field, []).append(message)

        previous_status = self._stored_status()
        if previous_status is not None:
            try:
                self.validate_status_transition(self.status, previous_status=previous_status)
            except ValidationError as exc:
                for field, messages in exc.message_dict.items():
                    for message in messages:
                        add_error(field, message)

        if self.status == MonthlyAccessStatusType.ACTIVE and not self.booking_enabled:
            add_error('booking_enabled', 'Active monthly access must enable booking.')

        if self.status == MonthlyAccessStatusType.ACTIVE and self.deactivated_at is not None:
            add_error('deactivated_at', 'Active monthly access cannot keep a suspension timestamp.')

        if self.status in {MonthlyAccessStatusType.PENDING_PAYMENT, MonthlyAccessStatusType.SUSPENDED} and self.booking_enabled:
            add_error('booking_enabled', 'Pending or suspended monthly access cannot enable booking.')

        if self.status == MonthlyAccessStatusType.PENDING_PAYMENT:
            if self.activated_at is not None:
                add_error('activated_at', 'Pending monthly access cannot keep an activation timestamp.')
            if self.deactivated_at is not None:
                add_error('deactivated_at', 'Pending monthly access cannot keep a suspension timestamp.')
            if self.activated_by_id is not None:
                add_error('activated_by', 'Pending monthly access cannot keep an activation actor.')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.month = normalize_month_start(self.month)
        self.full_clean()
        super().save(*args, **kwargs)


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_entries',
    )
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    entity_type = models.CharField(max_length=100)
    entity_id = models.PositiveBigIntegerField()
    description = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} {self.entity_type} #{self.entity_id}'
