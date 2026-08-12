"""Single policy for deciding how fixed-booking history is handled."""

from dataclasses import dataclass

from .fixed_booking_history import (
    can_recreate_fixed_booking_over_history,
    has_global_deactivation_history,
    has_student_cancelled_fixed_booking,
)
from .models import BookingStatus


@dataclass(frozen=True)
class FixedBookingHistoryDecision:
    action: str
    detail: str


def decide_fixed_booking_history(*, session, student, bookings):
    """Classify history without changing it.

    Only cancelled fixed-slot history with no recovery, move, student
    cancellation, or global-deactivation marker is eligible for restoration.
    The caller still checks current eligibility and capacity.
    """
    if any(booking.status == BookingStatus.BOOKED for booking in bookings):
        return FixedBookingHistoryDecision('ALREADY_BOOKED', 'Ya existe una reserva activa.')

    history = {session.id: bookings}
    if has_global_deactivation_history(session=session, historical_bookings_by_session_id=history):
        return FixedBookingHistoryDecision(
            'RESPECT_GLOBAL_DEACTIVATION',
            'Baja global registrada; requiere una accion explicita posterior.',
        )
    if has_student_cancelled_fixed_booking(
        session=session,
        student=student,
        historical_bookings_by_session_id=history,
    ):
        return FixedBookingHistoryDecision(
            'RESPECT_CANCELLED',
            'Cancelacion propia de un turno fijo; no se recrea.',
        )
    if can_recreate_fixed_booking_over_history(
        session=session,
        student=student,
        historical_bookings_by_session_id=history,
    ):
        return FixedBookingHistoryDecision(
            'RESTORE',
            'Historial tecnico o administrativo seguro para restauracion.',
        )
    return FixedBookingHistoryDecision(
        'HISTORY_PRESENT',
        'Historial ambiguo o no elegible para recreacion; no se recrea.',
    )
