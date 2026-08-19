"""Read-only fixed-capacity accounting shared by recovery reads and writes."""

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from .fixed_booking_audit import audit_expected_fixed_bookings
from .fixed_booking_policy import decide_fixed_booking_history
from .models import Booking, BookingStatus, FixedBookingCapacityConflict, User


@dataclass(frozen=True)
class FixedCapacityAssessment:
    session_id: int
    capacity: int
    active_booking_count: int
    pending_fixed_student_ids: tuple[int, ...]

    @property
    def committed_count(self):
        return self.active_booking_count + len(self.pending_fixed_student_ids)

    @property
    def available_recovery_spots(self):
        return max(self.capacity - self.committed_count, 0)

    @property
    def has_fixed_capacity_conflict(self):
        return self.committed_count > self.capacity


def assess_fixed_capacity(*, session, locked_bookings=None):
    """Calculate fixed commitments without writing or reconciling bookings.

    Expected fixed pairs come from the same audit candidate policy used by the
    repair command. A fixed student already represented by any active booking
    is not counted twice.
    """
    if locked_bookings is None:
        active_bookings = list(
            Booking.objects.filter(session_id=session.pk, status=BookingStatus.BOOKED)
            .only('id', 'student_id', 'source', 'used_recovery_credit_id')
        )
    else:
        active_bookings = [item for item in locked_bookings if item.status == BookingStatus.BOOKED]
    active_student_ids = {booking.student_id for booking in active_bookings}
    expected_student_ids = {
        row['student_id']
        for row in audit_expected_fixed_bookings(start_date=session.date, end_date=session.date)
        if row['session_id'] == session.pk
    }
    missing_student_ids = expected_student_ids - active_student_ids
    bookings_by_student_id = {student_id: [] for student_id in missing_student_ids}
    if locked_bookings is not None:
        for booking in locked_bookings:
            if booking.student_id in bookings_by_student_id:
                bookings_by_student_id[booking.student_id].append(booking)

    pending_fixed_student_ids = _materializable_fixed_student_ids(
        session=session,
        expected_student_ids=expected_student_ids,
        active_student_ids=active_student_ids,
        bookings_by_student_id=bookings_by_student_id if locked_bookings is not None else None,
    )
    return FixedCapacityAssessment(
        session_id=session.pk,
        capacity=session.capacity,
        active_booking_count=len(active_bookings),
        pending_fixed_student_ids=pending_fixed_student_ids,
    )


def assess_fixed_capacities(*, sessions):
    """Return read-only fixed-capacity assessments for a session collection.

    The expected-fixed audit is deliberately evaluated once over the full date
    range, then reduced to the requested sessions.  Recovery availability uses
    this on its GET read model so it never repeats a whole-day audit for each
    session or compatible recovery credit.
    """
    sessions = list(sessions)
    if not sessions:
        return {}

    session_ids = {session.pk for session in sessions}
    active_counts = {}
    active_student_ids_by_session = {}
    for booking in Booking.objects.filter(
        session_id__in=session_ids,
        status=BookingStatus.BOOKED,
    ).only('session_id', 'student_id'):
        active_counts[booking.session_id] = active_counts.get(booking.session_id, 0) + 1
        active_student_ids_by_session.setdefault(booking.session_id, set()).add(booking.student_id)

    expected_student_ids_by_session = {}
    for row in audit_expected_fixed_bookings(
        start_date=min(session.date for session in sessions),
        end_date=max(session.date for session in sessions),
    ):
        if row['session_id'] in session_ids:
            expected_student_ids_by_session.setdefault(row['session_id'], set()).add(row['student_id'])

    missing_student_ids_by_session = {
        session_id: expected_student_ids - active_student_ids_by_session.get(session_id, set())
        for session_id, expected_student_ids in expected_student_ids_by_session.items()
    }
    missing_student_ids = set().union(*missing_student_ids_by_session.values()) if missing_student_ids_by_session else set()
    bookings_by_session_student_id = {
        (session_id, student_id): []
        for session_id, student_ids in missing_student_ids_by_session.items()
        for student_id in student_ids
    }
    for booking in Booking.objects.filter(
        session_id__in=session_ids,
        student_id__in=missing_student_ids,
    ).only(
        'session_id', 'student_id', 'status', 'source', 'cancelled_by_id',
        'cancellation_reason', 'used_recovery_credit_id', 'moved_from_booking_id',
        'moved_to_session_id', 'cancellation_generates_recovery',
    ):
        bookings = bookings_by_session_student_id.get((booking.session_id, booking.student_id))
        if bookings is not None:
            bookings.append(booking)
    students_by_id = User.objects.in_bulk(missing_student_ids)

    return {
        session.pk: FixedCapacityAssessment(
            session_id=session.pk,
            capacity=session.capacity,
            active_booking_count=active_counts.get(session.pk, 0),
            pending_fixed_student_ids=_materializable_fixed_student_ids(
                session=session,
                expected_student_ids=expected_student_ids_by_session.get(session.pk, set()),
                active_student_ids=active_student_ids_by_session.get(session.pk, set()),
                bookings_by_student_id={
                    student_id: bookings_by_session_student_id[(session.pk, student_id)]
                    for student_id in missing_student_ids_by_session.get(session.pk, set())
                },
                students_by_id=students_by_id,
            ),
        )
        for session in sessions
    }


def _materializable_fixed_student_ids(
    *, session, expected_student_ids, active_student_ids, bookings_by_student_id=None, students_by_id=None,
):
    """Reserve only absent pairs that repair may create or restore."""
    missing_student_ids = expected_student_ids - active_student_ids
    if not missing_student_ids:
        return ()

    if bookings_by_student_id is None:
        bookings_by_student_id = {student_id: [] for student_id in missing_student_ids}
        for booking in Booking.objects.filter(
            session_id=session.pk,
            student_id__in=missing_student_ids,
        ).only(
            'student_id', 'status', 'source', 'cancelled_by_id',
            'cancellation_reason', 'used_recovery_credit_id', 'moved_from_booking_id',
            'moved_to_session_id', 'cancellation_generates_recovery',
        ):
            bookings_by_student_id[booking.student_id].append(booking)
    if students_by_id is None:
        students_by_id = User.objects.in_bulk(missing_student_ids)

    return tuple(sorted(
        student_id
        for student_id, bookings in bookings_by_student_id.items()
        if not bookings
        or decide_fixed_booking_history(
            session=session,
            student=students_by_id[student_id],
            bookings=bookings,
        ).action == 'RESTORE'
    ))


def ensure_recovery_capacity(*, session, locked_bookings=None):
    assessment = assess_fixed_capacity(session=session, locked_bookings=locked_bookings)
    if assessment.available_recovery_spots < 1:
        raise ValidationError({
            'session': ['This session has no capacity after reserving expected fixed bookings.'],
        })
    return assessment


def record_fixed_capacity_conflict(*, session, assessment, detail):
    """Persist the latest scheduler/POST conflict; never call from GET."""
    active_bookings = Booking.objects.filter(session_id=session.pk, status=BookingStatus.BOOKED).values(
        'student_id', 'source', 'used_recovery_credit_id',
    )
    conflict, _ = FixedBookingCapacityConflict.objects.update_or_create(
        session=session,
        defaults={
            'state': FixedBookingCapacityConflict.State.PENDING,
            'capacity': assessment.capacity,
            'active_booking_count': assessment.active_booking_count,
            'expected_fixed_student_ids': list(assessment.pending_fixed_student_ids),
            'active_booking_snapshot': list(active_bookings),
            'detail': detail,
        },
    )
    return conflict
