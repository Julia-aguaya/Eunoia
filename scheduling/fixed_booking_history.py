"""Safe history predicates and restoration shared by fixed-booking workflows."""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    Booking,
    BookingCancellationReason,
    BookingSource,
    BookingStatus,
    ClassSession,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    SessionStatus,
    StudentMonthlyPlan,
    StudentMonthlyPlanSlot,
    User,
    WeeklyClassSlot,
    normalize_month_start,
)


def has_blocking_fixed_plan_history(*, session, historical_bookings_by_session_id):
    return bool(historical_bookings_by_session_id.get(session.id))


def has_student_cancelled_fixed_booking(*, session, student, historical_bookings_by_session_id):
    return any(
        booking.status == BookingStatus.CANCELLED
        and booking.source == BookingSource.FIXED_SLOT
        and booking.cancelled_by_id == student.pk
        for booking in historical_bookings_by_session_id.get(session.id, [])
    )


def has_global_deactivation_history(*, session, historical_bookings_by_session_id):
    return any(
        booking.cancellation_reason == BookingCancellationReason.GLOBAL_DEACTIVATION
        for booking in historical_bookings_by_session_id.get(session.id, [])
    )


def can_recreate_fixed_booking_over_history(*, session, student, historical_bookings_by_session_id):
    historical_bookings = historical_bookings_by_session_id.get(session.id, [])
    if not historical_bookings:
        return False
    if has_global_deactivation_history(
        session=session,
        historical_bookings_by_session_id=historical_bookings_by_session_id,
    ):
        return False

    for booking in historical_bookings:
        if booking.status != BookingStatus.CANCELLED:
            return False
        if booking.source != BookingSource.FIXED_SLOT:
            return False
        if booking.used_recovery_credit_id is not None:
            return False
        if booking.moved_from_booking_id is not None or booking.moved_to_session_id is not None:
            return False
        if booking.cancellation_generates_recovery:
            return False
        if booking.cancelled_by_id == student.pk:
            return False

    return True


def can_restore_obsolete_fixed_booking(
    *, booking, session, student, context_is_eligible=None, locked_session_bookings=None,
):
    if not student.is_active:
        return False
    if booking.status != BookingStatus.CANCELLED:
        return False
    if booking.source != BookingSource.FIXED_SLOT:
        return False
    if booking.cancelled_at is None:
        return False
    if booking.cancelled_by_id is not None:
        return False
    if booking.cancellation_generates_recovery:
        return False
    if booking.used_recovery_credit_id is not None:
        return False
    if booking.moved_from_booking_id is not None or booking.moved_to_session_id is not None:
        return False
    return _has_restorable_fixed_booking_context(
        booking=booking,
        session=session,
        student=student,
        context_is_eligible=context_is_eligible,
        locked_session_bookings=locked_session_bookings,
    )


def _has_restorable_fixed_booking_context(
    *, booking, session, student, context_is_eligible=None, locked_session_bookings=None,
):
    if context_is_eligible is None:
        context_is_eligible = fixed_booking_context_is_eligible(student=student, session=session)
    if not context_is_eligible:
        return False

    if locked_session_bookings is None:
        active_bookings = [
            item for item in Booking.objects.filter(session_id=session.pk, status=BookingStatus.BOOKED)
            if item.pk != booking.pk
        ]
    else:
        active_bookings = [
            item for item in locked_session_bookings
            if item.status == BookingStatus.BOOKED and item.pk != booking.pk
        ]
    if len(active_bookings) >= session.capacity:
        return False
    if any(item.student_id == student.pk for item in active_bookings):
        return False
    return True


def find_restorable_obsolete_fixed_booking(
    *, session, student, historical_bookings_by_session_id, context_is_eligible=None, locked_session_bookings=None,
):
    if has_global_deactivation_history(
        session=session,
        historical_bookings_by_session_id=historical_bookings_by_session_id,
    ):
        return None
    return next(
        (
            booking
            for booking in historical_bookings_by_session_id.get(session.id, [])
            if can_restore_obsolete_fixed_booking(
                booking=booking,
                session=session,
                student=student,
                context_is_eligible=context_is_eligible,
                locked_session_bookings=locked_session_bookings,
            )
        ),
        None,
    )


def restore_obsolete_fixed_booking(*, session, student, historical_bookings_by_session_id):
    with transaction.atomic():
        locked_student, locked_session, locked_accesses, locked_plan, locked_plan_slots, locked_slots, locked_session_bookings = _lock_restore_context(
            student_id=student.pk,
            session_id=session.pk,
        )
        historical_booking = find_restorable_obsolete_fixed_booking(
            session=locked_session,
            student=locked_student,
            historical_bookings_by_session_id={
                locked_session.pk: [item for item in locked_session_bookings if item.student_id == locked_student.pk],
            },
            context_is_eligible=fixed_booking_context_is_eligible_locked(
                student=locked_student,
                session=locked_session,
                locked_accesses=locked_accesses,
                locked_plan=locked_plan,
                locked_plan_slots=locked_plan_slots,
                locked_slots=locked_slots,
            ),
            locked_session_bookings=locked_session_bookings,
        )
        if historical_booking is None:
            return False

        _restore_fixed_booking(historical_booking)
        return True


def restore_recreatable_fixed_booking(*, session, student, historical_bookings_by_session_id):
    with transaction.atomic():
        locked_student, locked_session, locked_accesses, locked_plan, locked_plan_slots, locked_slots, locked_session_bookings = _lock_restore_context(
            student_id=student.pk,
            session_id=session.pk,
        )
        locked_bookings = [item for item in locked_session_bookings if item.student_id == locked_student.pk]
        history = {locked_session.pk: locked_bookings}
        if not can_recreate_fixed_booking_over_history(
            session=locked_session,
            student=locked_student,
            historical_bookings_by_session_id=history,
        ):
            return False

        historical_booking = locked_bookings[0]
        if historical_booking.cancelled_at is None:
            return False
        if not _has_restorable_fixed_booking_context(
            booking=historical_booking,
            session=locked_session,
            student=locked_student,
            context_is_eligible=fixed_booking_context_is_eligible_locked(
                student=locked_student,
                session=locked_session,
                locked_accesses=locked_accesses,
                locked_plan=locked_plan,
                locked_plan_slots=locked_plan_slots,
                locked_slots=locked_slots,
            ),
            locked_session_bookings=locked_session_bookings,
        ):
            return False

        _restore_fixed_booking(historical_booking)
        return True


def materialize_fixed_booking_lock_context(*, student_id, session_id):
    """Read candidate IDs before locks; locked code only re-reads those simple rows."""
    session = ClassSession.objects.values('pk', 'section_id', 'date').get(pk=session_id)
    target_month = normalize_month_start(session['date'])
    plan_id = (
        StudentMonthlyPlan.objects.filter(
            student_id=student_id,
            section_id=session['section_id'],
            month__lte=target_month,
        )
        .order_by('-month', '-pk').values_list('pk', flat=True).first()
    )
    plan_slot_ids = []
    slot_ids = []
    if plan_id is not None:
        plan_slots = list(
            StudentMonthlyPlanSlot.objects.filter(monthly_plan_id=plan_id)
            .order_by('pk').values_list('pk', 'weekly_class_slot_id')
        )
        plan_slot_ids = [item[0] for item in plan_slots]
        slot_ids = [item[1] for item in plan_slots]
    session_booking_ids = list(
        Booking.objects.filter(session_id=session_id).order_by('pk').values_list('pk', flat=True)
    )
    pair_booking_ids = list(
        Booking.objects.filter(pk__in=session_booking_ids, student_id=student_id)
        .order_by('pk').values_list('pk', flat=True)
    )
    return {
        'student_id': student_id,
        'session_id': session_id,
        'access_ids': list(
            MonthlyAccessStatus.objects.filter(student_id=student_id)
            .order_by('pk').values_list('pk', flat=True)
        ),
        'plan_id': plan_id,
        'plan_slot_ids': plan_slot_ids,
        'slot_ids': slot_ids,
        'credit_ids': list(
            Booking.objects.filter(pk__in=pair_booking_ids, used_recovery_credit_id__isnull=False)
            .order_by('used_recovery_credit_id').values_list('used_recovery_credit_id', flat=True)
        ),
        'session_booking_ids': session_booking_ids,
    }


def lock_fixed_booking_context(*, lock_context):
    """Lock a pre-materialized context in the documented global order."""
    locked_student = User.objects.select_for_update().get(pk=lock_context['student_id'])
    locked_session = ClassSession.objects.select_for_update().get(pk=lock_context['session_id'])
    locked_accesses = list(
        MonthlyAccessStatus.objects.select_for_update()
        .filter(pk__in=lock_context['access_ids']).order_by('pk')
    )
    locked_plan = None
    if lock_context['plan_id'] is not None:
        locked_plan = StudentMonthlyPlan.objects.select_for_update().filter(pk=lock_context['plan_id']).first()
    locked_plan_slots = list(
        StudentMonthlyPlanSlot.objects.select_for_update()
        .filter(pk__in=lock_context['plan_slot_ids']).order_by('pk')
    )
    locked_slots = list(
        WeeklyClassSlot.objects.select_for_update().filter(pk__in=lock_context['slot_ids']).order_by('pk')
    )
    list(RecoveryCredit.objects.select_for_update().filter(pk__in=lock_context['credit_ids']).order_by('pk'))
    locked_session_bookings = list(
        Booking.objects.select_for_update()
        .filter(pk__in=lock_context['session_booking_ids']).order_by('pk')
    )
    return (
        locked_student,
        locked_session,
        locked_accesses,
        locked_plan,
        locked_plan_slots,
        locked_slots,
        locked_session_bookings,
    )


def _lock_restore_context(*, student_id, session_id):
    return lock_fixed_booking_context(
        lock_context=materialize_fixed_booking_lock_context(student_id=student_id, session_id=session_id),
    )


def fixed_booking_context_is_eligible(*, student, session):
    """Re-read the minimal current fixed-plan eligibility without relation traversal."""
    if not student.is_active or session.status != SessionStatus.SCHEDULED:
        return False

    target_month = normalize_month_start(session.date)
    if not MonthlyAccessStatus.objects.filter(
        student_id=student.pk,
        month=target_month,
        status=MonthlyAccessStatusType.ACTIVE,
        booking_enabled=True,
    ).exists():
        return False

    plan_id = (
        StudentMonthlyPlan.objects.filter(
            student_id=student.pk,
            section_id=session.section_id,
            month__lte=target_month,
        )
        .order_by('-month', '-pk')
        .values_list('pk', flat=True)
        .first()
    )
    if plan_id is None:
        return False

    return StudentMonthlyPlanSlot.objects.filter(
        monthly_plan_id=plan_id,
        weekly_class_slot__section_id=session.section_id,
        weekly_class_slot__weekday=session.date.isoweekday(),
        weekly_class_slot__start_time=session.start_time,
        weekly_class_slot__end_time=session.end_time,
        weekly_class_slot__is_active=True,
    ).filter(
        Q(weekly_class_slot__starts_on__isnull=True)
        | Q(weekly_class_slot__starts_on__lte=session.date),
        Q(weekly_class_slot__ends_on__isnull=True)
        | Q(weekly_class_slot__ends_on__gte=session.date),
    ).exists()


def fixed_booking_context_is_eligible_locked(
    *, student, session, locked_accesses, locked_plan, locked_plan_slots, locked_slots,
):
    """Evaluate fixed eligibility solely from canonical rows already locked by ID."""
    if not student.is_active or session.status != SessionStatus.SCHEDULED:
        return False

    target_month = normalize_month_start(session.date)
    if not any(
        access.month == target_month
        and access.status == MonthlyAccessStatusType.ACTIVE
        and access.booking_enabled
        for access in locked_accesses
    ):
        return False
    if locked_plan is None:
        return False

    slots_by_id = {slot.pk: slot for slot in locked_slots}
    for plan_slot in locked_plan_slots:
        slot = slots_by_id.get(plan_slot.weekly_class_slot_id)
        if slot is None:
            continue
        if slot.section_id != session.section_id:
            continue
        if slot.weekday != session.date.isoweekday():
            continue
        if slot.start_time != session.start_time or slot.end_time != session.end_time:
            continue
        if not slot.is_active:
            continue
        if slot.starts_on is not None and slot.starts_on > session.date:
            continue
        if slot.ends_on is not None and slot.ends_on < session.date:
            continue
        return True
    return False


def _restore_fixed_booking(historical_booking):
    Booking.objects.filter(pk=historical_booking.pk).update(
        status=BookingStatus.BOOKED,
        cancelled_at=None,
        cancelled_by_id=None,
        cancellation_generates_recovery=False,
        cancellation_reason=None,
        updated_at=timezone.now(),
    )
    historical_booking.status = BookingStatus.BOOKED
    historical_booking.cancelled_at = None
    historical_booking.cancelled_by_id = None
    historical_booking.cancellation_generates_recovery = False
    historical_booking.cancellation_reason = None
