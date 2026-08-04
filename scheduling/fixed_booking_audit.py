"""Read-only audit for expected fixed-plan bookings.

The module only evaluates ORM querysets. It never reconciles, creates, updates,
or deletes records, so it is safe to run against the current production data.
"""

from collections import defaultdict

from django.db.models import Prefetch

from .models import (
    Booking,
    BookingStatus,
    ClassSession,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    RecoveryCreditSource,
    SessionStatus,
    StudentMonthlyPlan,
    StudentMonthlyPlanSlot,
    normalize_month_start,
)


CSV_COLUMNS = (
    'student_id', 'nombre', 'email', 'plan_id', 'slot_id', 'session_id',
    'fecha', 'section', 'hora', 'access_status', 'booking_enabled',
    'booking_id', 'booking_status', 'booking_source', 'cancelled_by_id',
    'cancelled_at', 'cancellation_generates_recovery', 'recovery_credit_id',
    'clasificacion',
)


def _recovery_credit_id(booking, credits_by_student_session):
    if booking is None:
        return None
    if booking.used_recovery_credit_id is not None:
        return booking.used_recovery_credit_id
    if not booking.cancellation_generates_recovery:
        return None
    credits = credits_by_student_session.get((booking.student_id, booking.session_id), ())
    return next((credit.id for credit in credits if credit.source == RecoveryCreditSource.TIMELY_CANCELLATION), None)


def _cancelled_classification(booking, recovery_credit_id):
    has_recovery = booking.cancellation_generates_recovery or recovery_credit_id is not None
    recovery_suffix = 'with_recovery' if has_recovery else 'without_recovery'
    if booking.cancelled_by_id == booking.student_id:
        return f'B_cancelled_student_{recovery_suffix}'
    if booking.cancelled_by_id is not None:
        return f'B_cancelled_staff_{recovery_suffix}'
    return f'B_cancelled_technical_or_other_{recovery_suffix}'


def classify_bookings(bookings, credits_by_student_session=None):
    """Return the deterministic representative booking and A-E classification.

    A is one active booking, regardless of historical rows. B is cancellation-only.
    C has one or more non-booked, non-cancelled statuses. D has no rows. E is a
    corrupted history: duplicate active rows or an unrecognised status.
    """
    credits_by_student_session = credits_by_student_session or {}
    bookings = sorted(bookings, key=lambda booking: booking.id)
    if not bookings:
        return None, 'D_never_booked', None

    active = [booking for booking in bookings if booking.status == BookingStatus.BOOKED]
    known_statuses = {choice for choice, _ in BookingStatus.choices}
    unknown = [booking for booking in bookings if booking.status not in known_statuses]
    if len(active) > 1:
        return active[0], 'E_multiple_active_bookings', _recovery_credit_id(active[0], credits_by_student_session)
    if unknown:
        return unknown[0], 'E_unrecognised_booking_status', _recovery_credit_id(unknown[0], credits_by_student_session)
    if active:
        return active[0], 'A_booked', _recovery_credit_id(active[0], credits_by_student_session)

    cancelled = [booking for booking in bookings if booking.status == BookingStatus.CANCELLED]
    if len(cancelled) == len(bookings):
        representative = max(cancelled, key=lambda booking: (booking.cancelled_at is not None, booking.cancelled_at, booking.id))
        recovery_credit_id = _recovery_credit_id(representative, credits_by_student_session)
        return representative, _cancelled_classification(representative, recovery_credit_id), recovery_credit_id

    representative = next(booking for booking in bookings if booking.status != BookingStatus.CANCELLED)
    return representative, f'C_other_status_{representative.status}', _recovery_credit_id(representative, credits_by_student_session)


def audit_expected_fixed_bookings(*, start_date, end_date):
    """Yield one row per expected student/plan-slot/scheduled-session pair.

    An expected pair requires the effective plan for that section, an active and
    effective plan slot matching section/day/time, and explicit active monthly
    access with booking enabled for the session month. This deliberately does
    not use the first-ten-days operational-access fallback.
    """
    sessions = list(
        ClassSession.objects.select_related('section')
        .filter(date__range=(start_date, end_date), status=SessionStatus.SCHEDULED)
        .order_by('date', 'start_time', 'section_id', 'id')
    )
    if not sessions:
        return

    months = {normalize_month_start(session.date) for session in sessions}
    accesses = MonthlyAccessStatus.objects.select_related('student').filter(
        month__in=months,
        status=MonthlyAccessStatusType.ACTIVE,
        booking_enabled=True,
        student__is_active=True,
    ).order_by('student_id', 'month')
    students_by_month = defaultdict(list)
    for access in accesses:
        students_by_month[access.month].append(access)

    student_ids = {access.student_id for access in accesses}
    plans = (
        StudentMonthlyPlan.objects.filter(student_id__in=student_ids, month__lte=max(months))
        .select_related('student', 'section')
        .prefetch_related(Prefetch('plan_slots', queryset=StudentMonthlyPlanSlot.objects.select_related('weekly_class_slot')))
        .order_by('student_id', 'section_id', '-month', '-id')
    )
    effective_plans = {}
    for plan in plans:
        key = (plan.student_id, plan.section_id)
        effective_plans.setdefault(key, []).append(plan)

    bookings_by_pair = defaultdict(list)
    for booking in Booking.objects.filter(session__in=sessions, student_id__in=student_ids).select_related('student').order_by('id'):
        bookings_by_pair[(booking.student_id, booking.session_id)].append(booking)

    credits_by_student_session = defaultdict(list)
    for credit in RecoveryCredit.objects.filter(
        student_id__in=student_ids,
        origin_session__in=sessions,
    ).order_by('id'):
        credits_by_student_session[(credit.student_id, credit.origin_session_id)].append(credit)

    for session in sessions:
        for access in students_by_month[normalize_month_start(session.date)]:
            plans_for_section = effective_plans.get((access.student_id, session.section_id), ())
            plan = next((item for item in plans_for_section if item.month <= normalize_month_start(session.date)), None)
            if plan is None:
                continue
            matching_slot = next((
                plan_slot for plan_slot in plan.plan_slots.all()
                if plan_slot.weekly_class_slot.section_id == session.section_id
                and plan_slot.weekly_class_slot.start_time == session.start_time
                and plan_slot.weekly_class_slot.end_time == session.end_time
                and plan_slot.weekly_class_slot.is_effective_on(session.date)
            ), None)
            if matching_slot is None:
                continue
            booking, classification, recovery_credit_id = classify_bookings(
                bookings_by_pair[(access.student_id, session.id)], credits_by_student_session,
            )
            yield {
                'student_id': access.student_id,
                'nombre': access.student.get_full_name(),
                'email': access.student.email,
                'plan_id': plan.id,
                'slot_id': matching_slot.id,
                'session_id': session.id,
                'fecha': session.date.isoformat(),
                'section': session.section.code,
                'hora': session.start_time.strftime('%H:%M'),
                'access_status': access.status,
                'booking_enabled': access.booking_enabled,
                'booking_id': booking.id if booking else None,
                'booking_status': booking.status if booking else None,
                'booking_source': booking.source if booking else None,
                'cancelled_by_id': booking.cancelled_by_id if booking else None,
                'cancelled_at': booking.cancelled_at.isoformat() if booking and booking.cancelled_at else None,
                'cancellation_generates_recovery': booking.cancellation_generates_recovery if booking else None,
                'recovery_credit_id': recovery_credit_id,
                'clasificacion': classification,
            }
