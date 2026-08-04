"""Conservative repair workflow for missing fixed-slot bookings."""

import logging
import time

from django.core.exceptions import ValidationError
from django.db import OperationalError, connection, transaction

from .fixed_booking_audit import audit_expected_fixed_bookings
from .fixed_booking_history import (
    can_recreate_fixed_booking_over_history,
    fixed_booking_context_is_eligible_locked,
    find_restorable_obsolete_fixed_booking,
    has_global_deactivation_history,
    has_student_cancelled_fixed_booking,
    lock_fixed_booking_context,
    materialize_fixed_booking_lock_context,
    _restore_fixed_booking,
)
from .models import Booking, BookingStatus, ClassSession, User


logger = logging.getLogger(__name__)
MYSQL_RETRY_ERRNOS = frozenset((2006, 2013))
MAX_CREATE_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.05


class CandidateRepairError(RuntimeError):
    """Terminal repair failure with enough context for the command to report it."""

    def __init__(self, *, audit_row, attempts, errno, detail, reconnect_error=None):
        self.student_id = audit_row['student_id']
        self.session_id = audit_row['session_id']
        self.attempts = attempts
        self.errno = errno
        self.pending = True
        self.detail = detail
        self.reconnect_error = reconnect_error
        super().__init__(
            f'Fixed-booking repair pending for student_id={self.student_id} '
            f'session_id={self.session_id} attempts={attempts} errno={errno}: {detail}'
        )


def _history_decision(*, session, student, bookings):
    if any(booking.status == BookingStatus.BOOKED for booking in bookings):
        return 'ALREADY_BOOKED', 'Ya existe una reserva activa.'

    historical_bookings_by_session_id = {session.id: bookings}
    if has_global_deactivation_history(
        session=session,
        historical_bookings_by_session_id=historical_bookings_by_session_id,
    ):
        return 'RESPECT_GLOBAL_DEACTIVATION', 'Baja global registrada; requiere una accion explicita posterior.'
    if has_student_cancelled_fixed_booking(
        session=session,
        student=student,
        historical_bookings_by_session_id=historical_bookings_by_session_id,
    ):
        return 'RESPECT_CANCELLED', 'Cancelacion propia de un turno fijo; no se recrea.'

    if can_recreate_fixed_booking_over_history(
        session=session,
        student=student,
        historical_bookings_by_session_id=historical_bookings_by_session_id,
    ):
        return 'HISTORY_PRESENT', 'Historial administrativo/tecnico seguro para el reconciliador; repair no recrea historiales.'
    return 'HISTORY_PRESENT', 'Historial ambiguo o no elegible para recreacion; no se recrea.'


def _row(audit_row, *, action, mode, detail):
    return {
        'student_id': audit_row['student_id'],
        'alumna': audit_row['nombre'],
        'session_id': audit_row['session_id'],
        'fecha': audit_row['fecha'],
        'horario': audit_row['hora'],
        'seccion': audit_row['section'],
        'estado_encontrado': audit_row['clasificacion'],
        'accion': action,
        'modo': mode,
        'detalle': detail,
    }


def _validation_action(exc):
    messages = [message for field_messages in exc.message_dict.values() for message in field_messages]
    if any('capacity' in message.lower() for message in messages):
        return 'SKIP_CAPACITY', ' '.join(messages)
    return 'SKIP_VALIDATION', ' '.join(messages)


def _mysql_disconnect_errno(exc):
    """Find a MySQL disconnect errno through Django/driver exception wrappers."""
    pending = [exc]
    seen = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, int) and current in MYSQL_RETRY_ERRNOS:
            return current
        if isinstance(current, BaseException):
            pending.extend(current.args)
            if current.__cause__ is not None:
                pending.append(current.__cause__)
            if current.__context__ is not None:
                pending.append(current.__context__)
        elif isinstance(current, (tuple, list)):
            pending.extend(current)
    return None


def _is_retryable_mysql_disconnect(exc):
    return connection.vendor == 'mysql' and isinstance(exc, OperationalError) and _mysql_disconnect_errno(exc) is not None


def _retry_backoff(attempt):
    time.sleep(RETRY_BACKOFF_SECONDS * attempt)


def _raise_candidate_error(*, audit_row, attempts, original_error, detail, reconnect_error=None):
    raise CandidateRepairError(
        audit_row=audit_row,
        attempts=attempts,
        errno=_mysql_disconnect_errno(original_error),
        detail=detail,
        reconnect_error=reconnect_error,
    ) from original_error


def _repair_missing_candidate(*, audit_row, mode):
    """Create one missing candidate, retrying only confirmed MySQL disconnects."""
    last_errno = None
    for attempt in range(1, MAX_CREATE_ATTEMPTS + 1):
        try:
            lock_context = materialize_fixed_booking_lock_context(
                student_id=audit_row['student_id'], session_id=audit_row['session_id'],
            )
            with transaction.atomic():
                (
                    student, session, locked_accesses, locked_plan, locked_plan_slots,
                    locked_slots, locked_session_bookings,
                ) = lock_fixed_booking_context(lock_context=lock_context)
                if not student.is_active:
                    return _row(
                        audit_row,
                        action='SKIP_GLOBALLY_INACTIVE',
                        mode=mode,
                        detail='La alumna fue dada de baja globalmente durante la reparacion.',
                    )
                bookings = [item for item in locked_session_bookings if item.student_id == student.pk]
                # The audit chooses candidates before locking. The write decision
                # re-reads only this pair's current eligibility while locks are held.
                context_is_eligible = fixed_booking_context_is_eligible_locked(
                    student=student,
                    session=session,
                    locked_accesses=locked_accesses,
                    locked_plan=locked_plan,
                    locked_plan_slots=locked_plan_slots,
                    locked_slots=locked_slots,
                )
                if not context_is_eligible:
                    return _row(
                        audit_row,
                        action='SKIP_NOT_ELIGIBLE',
                        mode=mode,
                        detail='El par dejo de ser elegible durante la reparacion.',
                    )

                if bookings:
                    if any(booking.status == BookingStatus.BOOKED for booking in bookings):
                        action = 'RECOVERED_AFTER_AMBIGUOUS_COMMIT' if attempt > 1 else 'ALREADY_BOOKED'
                        return _row(
                            audit_row,
                            action=action,
                            mode=mode,
                            detail='La relectura encontro una reserva activa; no se recrea.',
                        )
                    action, detail = _history_decision(session=session, student=student, bookings=bookings)
                    return _row(audit_row, action=action, mode=mode, detail=detail)

                try:
                    Booking.objects.create_fixed_booking_while_locked(
                        session=session,
                        student=student,
                        context_is_eligible=context_is_eligible,
                        locked_bookings=bookings,
                    )
                except ValidationError as exc:
                    action, detail = _validation_action(exc)
                    return _row(audit_row, action=action, mode=mode, detail=detail)
                action = 'CREATED_AFTER_RETRY' if attempt > 1 else 'CREATED'
                return _row(
                    audit_row,
                    action=action,
                    mode=mode,
                    detail='Reserva fija creada sin historial previo.',
                )
        except OperationalError as exc:
            errno = _mysql_disconnect_errno(exc)
            if not _is_retryable_mysql_disconnect(exc):
                raise
            last_errno = errno
            if attempt == MAX_CREATE_ATTEMPTS:
                logger.exception(
                    'repair_fixed_bookings retry exhausted candidate=%s attempts=%s pending=%s errno=%s',
                    (audit_row['student_id'], audit_row['session_id']), attempt, True, errno,
                )
                _raise_candidate_error(
                    audit_row=audit_row,
                    attempts=attempt,
                    original_error=exc,
                    detail=f'Se agotaron los reintentos tras una desconexion MySQL: {exc}',
                )
            # The failed atomic block has exited before the connection is recycled.
            try:
                connection.close()
            except Exception as reconnect_exc:
                if not _is_retryable_mysql_disconnect(reconnect_exc):
                    _raise_candidate_error(
                        audit_row=audit_row,
                        attempts=attempt,
                        original_error=exc,
                        detail=f'Fallo no transitorio al cerrar la conexion para reintentar: {reconnect_exc}',
                        reconnect_error=reconnect_exc,
                    )
                logger.warning('repair_fixed_bookings transient close failure; retrying candidate=%s',
                               (audit_row['student_id'], audit_row['session_id']), exc_info=True)
                _retry_backoff(attempt)
                continue
            _retry_backoff(attempt)
            try:
                connection.ensure_connection()
            except Exception as reconnect_exc:
                if not _is_retryable_mysql_disconnect(reconnect_exc):
                    _raise_candidate_error(
                        audit_row=audit_row,
                        attempts=attempt,
                        original_error=exc,
                        detail=f'Fallo no transitorio al reconectar para reintentar: {reconnect_exc}',
                        reconnect_error=reconnect_exc,
                    )
                logger.warning('repair_fixed_bookings transient reconnect failure; retrying candidate=%s',
                               (audit_row['student_id'], audit_row['session_id']), exc_info=True)

    raise RuntimeError(f'Unexpected retry loop exit for errno {last_errno}')


def repair_expected_fixed_bookings(*, start_date, end_date, apply=False):
    """Return a report for auditor-selected pairs, creating only no-history pairs."""
    mode = 'apply' if apply else 'dry-run'
    results = []
    for audit_row in audit_expected_fixed_bookings(start_date=start_date, end_date=end_date):
        if audit_row['clasificacion'] != 'D_never_booked':
            if apply:
                # Apply locks the history before deciding whether an obsolete booking can be restored.
                lock_context = materialize_fixed_booking_lock_context(
                    student_id=audit_row['student_id'], session_id=audit_row['session_id'],
                )
                with transaction.atomic():
                    (
                        student, session, locked_accesses, locked_plan, locked_plan_slots,
                        locked_slots, locked_session_bookings,
                    ) = lock_fixed_booking_context(lock_context=lock_context)
                    if not student.is_active:
                        results.append(_row(
                            audit_row,
                            action='SKIP_GLOBALLY_INACTIVE',
                            mode=mode,
                            detail='La alumna fue dada de baja globalmente durante la reparacion.',
                        ))
                        continue
                    bookings = [item for item in locked_session_bookings if item.student_id == student.pk]
                    historical_bookings_by_session_id = {session.id: bookings}
                    context_is_eligible = fixed_booking_context_is_eligible_locked(
                        student=student,
                        session=session,
                        locked_accesses=locked_accesses,
                        locked_plan=locked_plan,
                        locked_plan_slots=locked_plan_slots,
                        locked_slots=locked_slots,
                    )
                    if not context_is_eligible:
                        results.append(_row(
                            audit_row,
                            action='SKIP_NOT_ELIGIBLE',
                            mode=mode,
                            detail='El par dejo de ser elegible durante la reparacion.',
                        ))
                        continue
                    historical_booking = find_restorable_obsolete_fixed_booking(
                        session=session,
                        student=student,
                        historical_bookings_by_session_id=historical_bookings_by_session_id,
                        context_is_eligible=context_is_eligible,
                        locked_session_bookings=locked_session_bookings,
                    )
                    if historical_booking is not None:
                        _restore_fixed_booking(historical_booking)
                        action, detail = 'RESTORED', 'Reserva fija tecnica restaurada conservando su identidad.'
                    else:
                        action, detail = _history_decision(session=session, student=student, bookings=bookings)
                    results.append(_row(audit_row, action=action, mode=mode, detail=detail))
                continue

            session = ClassSession.objects.get(pk=audit_row['session_id'])
            student = User.objects.get(pk=audit_row['student_id'])
            if not student.is_active:
                results.append(_row(
                    audit_row,
                    action='SKIP_GLOBALLY_INACTIVE',
                    mode=mode,
                    detail='La alumna fue dada de baja globalmente.',
                ))
                continue
            bookings = list(Booking.objects.filter(session=session, student=student).order_by('id'))
            historical_bookings_by_session_id = {session.id: bookings}
            historical_booking = find_restorable_obsolete_fixed_booking(
                session=session,
                student=student,
                historical_bookings_by_session_id=historical_bookings_by_session_id,
            )
            if historical_booking is not None:
                action, detail = 'WOULD_RESTORE', 'Reserva fija tecnica elegible para restauracion.'
            else:
                action, detail = _history_decision(session=session, student=student, bookings=bookings)
            results.append(_row(audit_row, action=action, mode=mode, detail=detail))
            continue

        if not apply:
            results.append(_row(
                audit_row,
                action='WOULD_CREATE',
                mode=mode,
                detail='Par elegible sin historial de reservas.',
            ))
            continue

        results.append(_repair_missing_candidate(audit_row=audit_row, mode=mode))

    return results
