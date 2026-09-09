"""Conservative, approval-gated remediation of automatic access-impact cancellations."""

from django.db import transaction

from .fixed_booking_repair import repair_expected_fixed_bookings
from .models import (
    Booking,
    BookingCancellationOrigin,
    BookingRemediationApproval,
    BookingSource,
    BookingStatus,
    MonthlyAccessStatus,
    StudentMonthlyPlan,
    User,
    normalize_month_start,
)


def _candidate_bookings(*, start_date, end_date):
    return (
        Booking.objects.select_related('student', 'session', 'session__section')
        .filter(
            status=BookingStatus.CANCELLED,
            source=BookingSource.FIXED_SLOT,
            session__date__range=(start_date, end_date),
        )
        .filter(
            cancellation_origin=BookingCancellationOrigin.AUTOMATIC_ACCESS_IMPACT,
        )
        .union(
            Booking.objects.select_related('student', 'session', 'session__section')
            .filter(
                status=BookingStatus.CANCELLED,
                source=BookingSource.FIXED_SLOT,
                session__date__range=(start_date, end_date),
                remediation_approval__isnull=False,
            )
        )
        .order_by('pk')
    )


def _candidate_kind(booking):
    if booking.cancellation_origin == BookingCancellationOrigin.AUTOMATIC_ACCESS_IMPACT:
        return 'AUTOMATIC'
    return 'APPROVED_LEGACY'


def remediate_automatic_access_impact(*, start_date, end_date, apply=False):
    """Restore only proven automatic or explicitly approved legacy cancellations.

    Null provenance is intentionally unknown. It is never a remediation candidate.
    """
    mode = 'apply' if apply else 'dry-run'
    rows = []
    restored_student_ids = set()

    for candidate in _candidate_bookings(start_date=start_date, end_date=end_date):
        kind = _candidate_kind(candidate)
        if candidate.student.manual_suspension:
            rows.append({'student_id': candidate.student_id, 'booking_id': candidate.pk, 'action': 'RESPECT_MANUAL_SUSPENSION', 'mode': mode})
            continue
        if not apply:
            rows.append({'student_id': candidate.student_id, 'booking_id': candidate.pk, 'action': f'WOULD_RESTORE_{kind}', 'mode': mode})
            restored_student_ids.add(candidate.student_id)
            continue

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related('student', 'session', 'session__section')
                .get(pk=candidate.pk)
            )
            student = User.objects.select_for_update().get(pk=booking.student_id)
            if student.manual_suspension:
                rows.append({'student_id': student.pk, 'booking_id': booking.pk, 'action': 'RESPECT_MANUAL_SUSPENSION', 'mode': mode})
                continue
            approved = BookingRemediationApproval.objects.filter(booking_id=booking.pk).exists()
            if (
                booking.cancellation_origin != BookingCancellationOrigin.AUTOMATIC_ACCESS_IMPACT
                and not approved
            ):
                rows.append({'student_id': student.pk, 'booking_id': booking.pk, 'action': 'SKIP_UNAPPROVED_ORIGIN', 'mode': mode})
                continue

            kind = _candidate_kind(booking)

            # A qualifying booking is the only evidence allowed to restore its exact account/month/plan scope.
            if not student.is_active:
                student.is_active = True
                student.save(update_fields=['is_active', 'updated_at'])
            booking.student = student
            month = normalize_month_start(booking.session.date)
            MonthlyAccessStatus.objects.filter(student=student, month=month, booking_enabled=False).update(booking_enabled=True)
            StudentMonthlyPlan.objects.filter(
                student=student, month=month, section=booking.session.section, is_active=False,
            ).update(is_active=True)
            try:
                booking.restore_technical_fixed_booking()
            except Exception:
                transaction.set_rollback(True)
                rows.append({'student_id': student.pk, 'booking_id': booking.pk, 'action': 'SKIP_RESTORE_SAFEGUARD', 'mode': mode})
                continue
            rows.append({'student_id': student.pk, 'booking_id': booking.pk, 'action': f'RESTORED_{kind}', 'mode': mode})
            restored_student_ids.add(student.pk)

    # Only create missing future fixed bookings for students with a proven restored cancellation.
    if restored_student_ids:
        for booking_row in repair_expected_fixed_bookings(
            start_date=start_date,
            end_date=end_date,
            apply=apply,
            student_ids=restored_student_ids,
            only_missing=True,
        ):
            rows.append({
                'student_id': booking_row['student_id'],
                'booking_id': '',
                'action': booking_row['accion'],
                'mode': mode,
            })
    return rows
