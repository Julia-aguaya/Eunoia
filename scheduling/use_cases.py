from dataclasses import dataclass

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .application.recovery_credits import (
    ManualRecoveryExpiration,
    RecoveryCreditBulkExpiration,
    expire_overdue_recovery_credits,
    expire_recovery_credit,
)
from .audit import (
    log_staff_class_session_cancelled,
    log_staff_holiday_closure_applied,
    log_staff_manual_recovery_granted,
    log_staff_monthly_access_change,
)
from .models import (
    Booking,
    BookingSource,
    ClassSession,
    HolidayClosure,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    SessionStatus,
    WeeklyClassSlot,
    normalize_month_start,
)


@dataclass(frozen=True)
class HolidayClosureApplication:
    closure: HolidayClosure
    created: bool
    result: dict


@dataclass(frozen=True)
class MonthlyAccessToggle:
    access: MonthlyAccessStatus
    activated: bool


@dataclass(frozen=True)
class MonthlyAccessChange:
    access: MonthlyAccessStatus
    created: bool
    changed: bool


@dataclass(frozen=True)
class CreateBookingResult:
    booking: Booking
    session: ClassSession
    recovery_credit: RecoveryCredit | None


@dataclass(frozen=True)
class CancelBookingResult:
    booking: Booking
    recovery_credit: RecoveryCredit


@dataclass(frozen=True)
class MarkBookingAttendanceResult:
    booking: Booking


@dataclass(frozen=True)
class GenerateClassSessionsResult:
    created_count: int
    skipped_duplicates: int
    inspected_matches: int


@dataclass(frozen=True)
class CancelClassSessionResult:
    session: ClassSession
    active_bookings: int
    created_credits: int
    existing_credits: int


def _sync_monthly_plan_bookings_for_published_sessions(*, start_date, end_date, section_code=None):
    sessions = list(
        ClassSession.objects.select_related('slot', 'section')
        .filter(
            date__range=(start_date, end_date),
            status=SessionStatus.SCHEDULED,
        )
        .order_by('date', 'start_time', 'pk')
    )
    if section_code:
        sessions = [session for session in sessions if session.section.code == section_code]
    if not sessions:
        return 0

    sessions_by_id = {session.id: session for session in sessions}
    sessions_by_month_and_signature = {}
    month_starts = set()
    for session in sessions:
        month_start = normalize_month_start(session.date)
        month_starts.add(month_start)
        sessions_by_month_and_signature.setdefault(
            (month_start, session.section_id, session.date.isoweekday(), session.start_time),
            [],
        ).append(session)

    active_accesses = list(
        MonthlyAccessStatus.objects.select_related('student')
        .filter(
            month__in=month_starts,
            status=MonthlyAccessStatusType.ACTIVE,
            booking_enabled=True,
        )
        .order_by('student_id', 'month')
    )
    if not active_accesses:
        return 0

    plan_cache = {}
    students_by_id = {}
    candidate_pairs = []
    candidate_student_ids = set()

    for access in active_accesses:
        students_by_id[access.student_id] = access.student
        candidate_student_ids.add(access.student_id)
        cache_key = (access.student_id, access.month)
        effective_plan = plan_cache.get(cache_key)
        if effective_plan is None:
            effective_plan = access.student.get_effective_monthly_plan_for(access.month)
            plan_cache[cache_key] = effective_plan
        if effective_plan is None:
            continue

        for slot in effective_plan.get_weekly_slots():
            session_signature = (
                access.month,
                effective_plan.section_id,
                slot.weekday,
                slot.start_time,
            )
            for session in sessions_by_month_and_signature.get(session_signature, []):
                if not slot.is_effective_on(session.date):
                    continue
                candidate_pairs.append((session.id, access.student_id))

    if not candidate_pairs:
        return 0

    existing_pairs = set(
        Booking.objects.filter(
            session_id__in=sessions_by_id.keys(),
            student_id__in=candidate_student_ids,
        ).values_list('session_id', 'student_id')
    )

    created_count = 0
    for session_id, student_id in candidate_pairs:
        pair = (session_id, student_id)
        if pair in existing_pairs:
            continue

        session = sessions_by_id[session_id]
        student = students_by_id[student_id]
        try:
            Booking.objects.create_booking(
                session=session,
                student=student,
                source=BookingSource.FIXED_SLOT,
            )
        except ValidationError:
            continue

        existing_pairs.add(pair)
        created_count += 1

    return created_count


def create_booking(*, session_id, student, used_recovery_credit_id=None, source=BookingSource.FIXED_SLOT):
    session = ClassSession.objects.select_related('section').get(pk=session_id)
    recovery_credit = None

    if used_recovery_credit_id:
        recovery_credit = (
            RecoveryCredit.objects.select_related('section', 'origin_session')
            .filter(pk=used_recovery_credit_id, student=student)
            .first()
        )
        if recovery_credit is None:
            raise ValidationError({'used_recovery_credit': ['Recovery credit is not available for this student.']})

    booking = Booking.objects.create_booking(
        session=session,
        student=student,
        source=source,
        used_recovery_credit=recovery_credit,
    )
    return CreateBookingResult(
        booking=booking,
        session=booking.session,
        recovery_credit=booking.used_recovery_credit,
    )


def cancel_booking(*, booking_id, student, actor=None, when=None):
    booking = Booking.objects.select_related('session', 'session__section').get(pk=booking_id, student=student)
    recovery_credit = booking.cancel_by_student(actor=actor or student, when=when)
    updated_booking = Booking.objects.select_related('session', 'session__section').get(pk=booking.pk)
    return CancelBookingResult(booking=updated_booking, recovery_credit=recovery_credit)


def cancel_class_session(*, session_id, actor=None, when=None, record_audit=False):
    cancellation_time = when or timezone.now()

    with transaction.atomic():
        session = (
            ClassSession.objects.select_for_update()
            .select_related('section', 'holiday_closure')
            .get(pk=session_id)
        )

        if session.status == SessionStatus.CANCELLED:
            raise ValidationError('La clase ya estaba cancelada.')

        if session.status == SessionStatus.HOLIDAY_CLOSED:
            raise ValidationError('La clase ya esta cerrada por feriado. No hace falta cancelarla aparte.')

        if session.ends_at() <= cancellation_time:
            raise ValidationError('Solo podés cancelar clases que todavia no terminaron.')

        session.status = SessionStatus.CANCELLED
        session.save(update_fields=['status', 'updated_at'])

        active_bookings = list(
            Booking.objects.select_related('student', 'session', 'session__section')
            .filter(session=session, status__in=Booking.active_statuses())
            .order_by('pk')
        )

        created_credits = 0
        existing_credits = 0
        for booking in active_bookings:
            _, created = RecoveryCredit.objects.grant_session_cancellation_credit(
                booking=booking,
                granted_by=actor,
                notes=(
                    f'Session cancelled by staff for {booking.session.date:%Y-%m-%d} '
                    f'at {booking.session.start_time:%H:%M}'
                ),
            )
            if created:
                created_credits += 1
            else:
                existing_credits += 1

    refreshed_session = ClassSession.objects.select_related('section', 'holiday_closure').get(pk=session.pk)
    result = CancelClassSessionResult(
        session=refreshed_session,
        active_bookings=len(active_bookings),
        created_credits=created_credits,
        existing_credits=existing_credits,
    )

    if record_audit:
        log_staff_class_session_cancelled(
            actor=actor,
            session=refreshed_session,
            result={
                'active_bookings': result.active_bookings,
                'created_credits': result.created_credits,
                'existing_credits': result.existing_credits,
            },
        )

    return result


def _mark_booking_attendance(*, booking_id, marker, when=None):
    booking = Booking.objects.select_related('session', 'session__section').get(pk=booking_id)
    updated_booking = marker(booking, when=when)
    refreshed_booking = Booking.objects.select_related('session', 'session__section').get(pk=updated_booking.pk)
    return MarkBookingAttendanceResult(booking=refreshed_booking)


def mark_booking_attended(*, booking_id, when=None):
    return _mark_booking_attendance(booking_id=booking_id, marker=Booking.mark_attended, when=when)


def mark_booking_no_show(*, booking_id, when=None):
    return _mark_booking_attendance(booking_id=booking_id, marker=Booking.mark_no_show, when=when)


def book_student_class(*, session_id, student, used_recovery_credit_id=None, source=BookingSource.FIXED_SLOT):
    return create_booking(
        session_id=session_id,
        student=student,
        used_recovery_credit_id=used_recovery_credit_id,
        source=source,
    )


def cancel_student_booking(*, booking_id, student, actor=None, when=None):
    return cancel_booking(booking_id=booking_id, student=student, actor=actor, when=when)


def generate_class_sessions(*, start_date, end_date, section_code=None, dry_run=False):
    if end_date < start_date:
        raise ValueError('end_date must be greater than or equal to start_date.')

    slots = WeeklyClassSlot.objects.select_related('section').filter(is_active=True)
    if section_code:
        slots = slots.filter(section__code=section_code)
        if not slots.exists():
            raise ValueError(f'No active weekly slots found for section "{section_code}".')

    holiday_closures = {
        closure.date: closure
        for closure in HolidayClosure.objects.filter(date__range=(start_date, end_date))
    }
    existing_sessions = set(
        ClassSession.objects.filter(date__range=(start_date, end_date)).values_list(
            'section_id',
            'date',
            'start_time',
        )
    )

    created_sessions = []
    skipped_duplicates = 0
    inspected_matches = 0

    for slot in slots:
        current_date = start_date
        while current_date <= end_date:
            if slot.is_effective_on(current_date):
                inspected_matches += 1
                session_key = (slot.section_id, current_date, slot.start_time)
                if session_key in existing_sessions:
                    skipped_duplicates += 1
                else:
                    created_sessions.append(
                        slot.build_session_for_date(
                            current_date,
                            holiday_closure=holiday_closures.get(current_date),
                        )
                    )
                    existing_sessions.add(session_key)
            current_date += timedelta(days=1)

    if not dry_run and created_sessions:
        ClassSession.objects.bulk_create(created_sessions)
    if not dry_run:
        _sync_monthly_plan_bookings_for_published_sessions(
            start_date=start_date,
            end_date=end_date,
            section_code=section_code,
        )

    return GenerateClassSessionsResult(
        created_count=len(created_sessions),
        skipped_duplicates=skipped_duplicates,
        inspected_matches=inspected_matches,
    )


def apply_holiday_closure(*, closure_date, reason, notes='', actor=None, record_audit=False):
    cleaned_notes = notes.strip()

    with transaction.atomic():
        closure, created = HolidayClosure.objects.get_or_create(
            date=closure_date,
            defaults={
                'reason': reason,
                'notes': cleaned_notes,
                'created_by': actor,
            },
        )

        fields_to_update = []
        if closure.reason != reason:
            closure.reason = reason
            fields_to_update.append('reason')
        if closure.notes != cleaned_notes:
            closure.notes = cleaned_notes
            fields_to_update.append('notes')
        if closure.created_by_id is None and actor is not None:
            closure.created_by = actor
            fields_to_update.append('created_by')
        if fields_to_update:
            fields_to_update.append('updated_at')
            closure.save(update_fields=fields_to_update)

        result = closure.apply(actor=actor)

    if record_audit:
        log_staff_holiday_closure_applied(actor=actor, closure=closure, result=result, created=created)

    return HolidayClosureApplication(closure=closure, created=created, result=result)


def grant_manual_recovery_credit(*, student, section, granted_by=None, notes='', reference_date=None, record_audit=False):
    credit = RecoveryCredit.objects.grant_manual_credit(
        student=student,
        section=section,
        granted_by=granted_by,
        reference_date=reference_date or timezone.localdate(),
        notes=notes.strip(),
    )

    if record_audit:
        log_staff_manual_recovery_granted(actor=granted_by, credit=credit)

    return credit


def _get_or_create_monthly_access(*, student, month=None):
    current_month = normalize_month_start(month or timezone.localdate())
    return MonthlyAccessStatus.objects.get_or_create(student=student, month=current_month)


def activate_student_monthly_access(*, student, actor=None, month=None, record_audit=False):
    access, created = _get_or_create_monthly_access(student=student, month=month)
    changed = not access.grants_operational_booking_access()
    access.activate_by_payment(actor=actor)

    if record_audit and changed:
        log_staff_monthly_access_change(actor=actor, access=access)

    return MonthlyAccessChange(access=access, created=created, changed=changed)


def suspend_student_monthly_access(*, student, actor=None, month=None, record_audit=False):
    access, created = _get_or_create_monthly_access(student=student, month=month)
    changed = access.status != MonthlyAccessStatusType.SUSPENDED or access.booking_enabled
    access.suspend_operational_access()

    if record_audit and changed:
        log_staff_monthly_access_change(actor=actor, access=access)

    return MonthlyAccessChange(access=access, created=created, changed=changed)


def toggle_student_monthly_access(*, student, actor=None, month=None, record_audit=False):
    access = student.get_monthly_access_for(month or timezone.localdate())

    if access is not None and access.grants_operational_booking_access():
        result = suspend_student_monthly_access(student=student, actor=actor, month=month, record_audit=record_audit)
        return MonthlyAccessToggle(access=result.access, activated=False)

    result = activate_student_monthly_access(student=student, actor=actor, month=month, record_audit=record_audit)
    return MonthlyAccessToggle(access=result.access, activated=True)
