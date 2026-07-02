from .models import AuditAction, AuditLog


def log_staff_monthly_access_change(*, actor, access):
    student = access.student
    is_active = access.status == 'active' and access.booking_enabled
    description = (
        f'Staff activo el acceso mensual de {student.get_full_name() or student.email}'
        if is_active
        else f'Staff suspendio el acceso mensual de {student.get_full_name() or student.email}'
    )
    return AuditLog.objects.create(
        actor=actor,
        action=AuditAction.STATUS_CHANGE,
        entity_type='MonthlyAccessStatus',
        entity_id=access.pk,
        description=description,
        payload={
            'scope': 'staff_portal',
            'student_id': student.pk,
            'student_email': student.email,
            'month': access.month.isoformat(),
            'status': access.status,
            'booking_enabled': access.booking_enabled,
        },
    )


def log_staff_manual_recovery_granted(*, actor, credit):
    student = credit.student
    return AuditLog.objects.create(
        actor=actor,
        action=AuditAction.CREDIT,
        entity_type='RecoveryCredit',
        entity_id=credit.pk,
        description=f'Staff otorgo una recuperacion manual para {student.get_full_name() or student.email}',
        payload={
            'scope': 'staff_portal',
            'student_id': student.pk,
            'student_email': student.email,
            'section_id': credit.section_id,
            'section_name': credit.section.name,
            'source': credit.source,
            'status': credit.status,
            'expires_at': credit.expires_at.isoformat(),
            'notes': credit.notes,
        },
    )


def log_staff_recovery_credit_expired(*, actor, credit, reason='manual'):
    student = credit.student
    if reason == 'overdue':
        description = f'Staff expiro por vencimiento una recuperacion de {student.get_full_name() or student.email}'
    else:
        description = f'Staff marco como vencida una recuperacion de {student.get_full_name() or student.email}'

    return AuditLog.objects.create(
        actor=actor,
        action=AuditAction.STATUS_CHANGE,
        entity_type='RecoveryCredit',
        entity_id=credit.pk,
        description=description,
        payload={
            'scope': 'staff_portal',
            'student_id': student.pk,
            'student_email': student.email,
            'section_id': credit.section_id,
            'section_name': credit.section.name,
            'source': credit.source,
            'status': credit.status,
            'expires_at': credit.expires_at.isoformat(),
            'origin_session_id': credit.origin_session_id,
            'reason': reason,
        },
    )


def log_staff_makeup_booking_removed(*, actor, booking, credit):
    student = booking.student
    return AuditLog.objects.create(
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type='Booking',
        entity_id=booking.pk,
        description=(
            f'Staff quito la recuperacion de una reserva de {student.get_full_name() or student.email}'
        ),
        payload={
            'scope': 'staff_portal',
            'student_id': student.pk,
            'student_email': student.email,
            'booking_id': booking.pk,
            'session_id': booking.session_id,
            'section_id': booking.session.section_id,
            'section_name': booking.session.section.name,
            'recovery_credit_id': credit.pk,
            'recovery_credit_source': credit.source,
            'restored_recovery_status': credit.status,
            'expires_at': credit.expires_at.isoformat(),
        },
    )


def log_staff_manual_recovery_expired(*, actor, credit):
    return log_staff_recovery_credit_expired(actor=actor, credit=credit, reason='manual')


def log_staff_holiday_closure_applied(*, actor, closure, result, created):
    action = AuditAction.CREATE if created else AuditAction.UPDATE
    verb = 'creo y aplico' if created else 'reaplico'
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type='HolidayClosure',
        entity_id=closure.pk,
        description=f'Staff {verb} un cierre por feriado para {closure.date:%d/%m/%Y}',
        payload={
            'scope': 'staff_portal',
            'date': closure.date.isoformat(),
            'reason': closure.reason,
            'notes': closure.notes,
            'created_by_id': closure.created_by_id,
            'recovery_credits_processed': closure.recovery_credits_processed,
            'updated_sessions': result['updated_sessions'],
            'created_credits': result['created_credits'],
            'existing_credits': result['existing_credits'],
        },
    )


def log_staff_class_session_cancelled(*, actor, session, result):
    return AuditLog.objects.create(
        actor=actor,
        action=AuditAction.STATUS_CHANGE,
        entity_type='ClassSession',
        entity_id=session.pk,
        description=f'Staff cancelo la clase #{session.pk} del {session.date:%d/%m/%Y} a las {session.start_time:%H:%M}',
        payload={
            'scope': 'staff_portal',
            'session_id': session.pk,
            'section_id': session.section_id,
            'section_name': session.section.name,
            'date': session.date.isoformat(),
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat(),
            'status': session.status,
            'active_bookings': result['active_bookings'],
            'created_credits': result['created_credits'],
            'existing_credits': result['existing_credits'],
        },
    )
