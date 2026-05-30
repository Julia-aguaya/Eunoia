from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.utils import timezone

from .application.recovery_credits import expire_recovery_credit
from .forms import (
    EmailAuthenticationForm,
    RequiredPasswordChangeForm,
    StaffHolidayClosureForm,
    StaffManualRecoveryCreditForm,
)
from .models import (
    AuditLog,
    Booking,
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
    User,
    UserRole,
    normalize_month_start,
)
from .use_cases import (
    activate_student_monthly_access,
    apply_holiday_closure,
    cancel_booking,
    create_booking,
    grant_manual_recovery_credit,
    suspend_student_monthly_access,
)


STUDENT_PORTAL_PREVIEW_LIMIT = 6
ADMIN_DETAIL_PREVIEW_LIMIT = 5
STAFF_AGENDA_WINDOW_DAYS = 7

BOOKING_ERROR_MESSAGES = {
    'Student must have a primary section before reserving.': 'Todavia no tenes una actividad principal configurada. Escribinos para habilitar tu agenda.',
    'Student can only reserve sessions in their primary section.': 'Esta clase corresponde a otra actividad. Solo podes reservar dentro de tu actividad principal.',
    'Student must have active monthly operational access for this session month.': 'Tu acceso operativo no permite reservar esta clase en este mes.',
    'This session is closed and cannot be booked.': 'Esta clase ya esta cerrada y no acepta nuevas reservas.',
    'This session has reached its capacity.': 'No quedan cupos disponibles para esta clase.',
    'Student already has an active booking for this session.': 'Ya tenes una reserva activa para esta clase.',
    'Recovery credit belongs to another student.': 'Esta recuperacion no pertenece a tu cuenta.',
    'Recovery credit can only be used within the same section.': 'Esta recuperacion corresponde a otra actividad y no aplica a esta clase.',
    'Recovery credit must be used for another session in the same section.': 'La recuperacion solo sirve para otra clase de la misma actividad, no para la sesion original.',
    'Recovery credit is not available.': 'La recuperacion elegida ya no esta disponible para usar.',
    'Recovery credit is expired.': 'La recuperacion elegida esta vencida y ya no puede usarse.',
    'Recovery credit is not available for this student.': 'La recuperacion elegida ya no esta disponible en tu portal.',
}

CANCELLATION_ERROR_MESSAGES = {
    'Only active bookings can be cancelled.': 'Esta reserva ya no esta activa, asi que no se puede cancelar de nuevo desde la web.',
    'Self-service cancellation is only allowed more than 2 hours before class start.': 'Esta reserva ya no puede cancelarse desde la web porque faltan 2 horas o menos para la clase.',
    'Only the booking student can cancel this booking.': 'Solo podes cancelar tus propias reservas.',
}

RECOVERY_MANAGEMENT_ERROR_MESSAGES = {
    'Only available recovery credits can be manually expired.': 'Solo se pueden marcar como vencidas las recuperaciones que siguen disponibles.',
}


def staff_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden(b'Staff access only.')
        return view_func(request, *args, **kwargs)

    return wrapped


def _get_default_portal_url(user):
    if user.is_staff:
        return reverse('admin-student-list')
    return reverse('dashboard')


def _build_admin_status_badges(access):
    if access is None:
        return {
            'operational_label': 'Sin estado cargado',
            'operational_tone': 'muted',
            'payment_label': 'Sin definir',
            'payment_tone': 'muted',
            'action_label': 'Activar acceso',
            'is_active': False,
            'summary_key': 'missing',
        }

    if access.grants_operational_booking_access():
        return {
            'operational_label': 'Activo',
            'operational_tone': 'success',
            'payment_label': 'Al dia',
            'payment_tone': 'success',
            'action_label': 'Suspender acceso',
            'is_active': True,
            'summary_key': 'active',
        }

    if access.status == MonthlyAccessStatusType.PENDING_PAYMENT:
        return {
            'operational_label': 'Pendiente de pago',
            'operational_tone': 'warning',
            'payment_label': 'Impaga',
            'payment_tone': 'danger',
            'action_label': 'Activar acceso',
            'is_active': False,
            'summary_key': 'pending',
        }

    return {
        'operational_label': 'Suspendido',
        'operational_tone': 'danger',
        'payment_label': 'Suspendido',
        'payment_tone': 'danger',
        'action_label': 'Activar acceso',
        'is_active': False,
        'summary_key': 'suspended',
    }


def _build_admin_student_detail_url(student_id, query=''):
    url = reverse('admin-student-detail', args=[student_id])
    if query:
        return f'{url}?{urlencode({"q": query})}'
    return url


def _build_admin_student_row(student, access, *, query=''):
    badges = _build_admin_status_badges(access)
    return {
        'student': student,
        'current_access': access,
        'section_name': student.primary_section.name if student.primary_section_id else 'Sin seccion principal',
        'detail_url': _build_admin_student_detail_url(student.pk, query=query),
        **badges,
    }


def _get_admin_students_context(*, query=''):
    current_month = normalize_month_start(timezone.localdate())
    students_qs = (
        User.objects.filter(role=UserRole.STUDENT)
        .select_related('primary_section')
        .prefetch_related(
            Prefetch(
                'monthly_access_statuses',
                queryset=MonthlyAccessStatus.objects.filter(month=current_month),
                to_attr='current_month_accesses',
            )
        )
    )

    if query:
        students_qs = students_qs.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))

    students = list(students_qs.order_by('last_name', 'first_name', 'email'))
    rows = []
    summary = {
        'active': 0,
        'pending': 0,
        'suspended': 0,
        'missing': 0,
    }

    for student in students:
        access = student.current_month_accesses[0] if student.current_month_accesses else None
        row = _build_admin_student_row(student, access, query=query)
        rows.append(row)
        summary[row['summary_key']] += 1

    return {
        'admin_students': rows,
        'admin_query': query,
        'admin_current_month': current_month,
        'admin_current_month_label': current_month.strftime('%m/%Y'),
        'admin_summary': summary,
    }


def _build_admin_redirect_url(query=''):
    url = reverse('admin-student-list')
    if query:
        return f'{url}?{urlencode({"q": query})}'
    return url


def _build_staff_class_agenda_url(*, date=None, section=''):
    url = reverse('admin-class-agenda')
    params = {}
    if date:
        params['date'] = date.isoformat() if hasattr(date, 'isoformat') else str(date)
    if section:
        params['section'] = str(section)
    if params:
        return f'{url}?{urlencode(params)}'
    return url


def _build_staff_class_session_detail_url(session_id, *, date=None, section=''):
    url = reverse('admin-class-session-detail', args=[session_id])
    params = {}
    if date:
        params['date'] = date.isoformat() if hasattr(date, 'isoformat') else str(date)
    if section:
        params['section'] = str(section)
    if params:
        return f'{url}?{urlencode(params)}'
    return url


def _parse_staff_agenda_date(raw_value):
    if not raw_value:
        return timezone.localdate()

    try:
        return ClassSession._meta.get_field('date').to_python(raw_value)
    except Exception:
        return timezone.localdate()


def _build_staff_class_agenda_context(*, data=None, closure_form=None):
    data = data or {}
    anchor_date = _parse_staff_agenda_date(data.get('date'))
    window_end = anchor_date + timedelta(days=STAFF_AGENDA_WINDOW_DAYS - 1)
    section_id = str(data.get('section', '')).strip()

    sessions_qs = (
        ClassSession.objects.select_related('section', 'holiday_closure')
        .filter(date__range=(anchor_date, window_end))
        .annotate(
            booked_count=Count(
                'bookings',
                filter=Q(bookings__status=BookingStatus.BOOKED),
                distinct=True,
            ),
            makeup_bookings_count=Count(
                'bookings',
                filter=Q(
                    bookings__status=BookingStatus.BOOKED,
                    bookings__used_recovery_credit__isnull=False,
                ),
                distinct=True,
            ),
        )
        .order_by('date', 'start_time', 'section__name')
    )

    active_section = None
    if section_id:
        active_section = Section.objects.filter(pk=section_id).first()
        if active_section is not None:
            sessions_qs = sessions_qs.filter(section=active_section)

    sessions = list(sessions_qs)
    session_ids = [session.pk for session in sessions]
    generated_recoveries_by_session = {
        row['origin_session_id']: row['total']
        for row in RecoveryCredit.objects.filter(
            source=RecoveryCreditSource.HOLIDAY_CLOSURE,
            origin_session_id__in=session_ids,
        )
        .values('origin_session_id')
        .annotate(total=Count('id'))
    }

    grouped_sessions = []
    grouped_sessions_by_date = {}
    for session in sessions:
        day_bucket = grouped_sessions_by_date.get(session.date)
        if day_bucket is None:
            day_bucket = {
                'date': session.date,
                'sessions': [],
            }
            grouped_sessions_by_date[session.date] = day_bucket
            grouped_sessions.append(day_bucket)

        day_bucket['sessions'].append(
            {
                'session': session,
                'booked_count': session.booked_count,
                'available_spots': max(session.capacity - session.booked_count, 0),
                'makeup_bookings_count': session.makeup_bookings_count,
                'generated_recoveries_count': generated_recoveries_by_session.get(session.pk, 0),
                'detail_url': _build_staff_class_session_detail_url(session.pk, date=anchor_date, section=section_id),
            }
        )

    closures = list(
        HolidayClosure.objects.filter(date__range=(anchor_date, window_end))
        .select_related('created_by')
        .order_by('date')
    )
    recent_closures = list(HolidayClosure.objects.select_related('created_by').order_by('-date')[:5])
    closure_form = closure_form or StaffHolidayClosureForm(initial={'date': anchor_date})
    closure_focus_date = closure_form['date'].value() or anchor_date
    closure_focus = HolidayClosure.objects.filter(date=_parse_staff_agenda_date(closure_focus_date)).first()
    closure_focus_summary = None

    if closure_focus is not None:
        closed_sessions_qs = ClassSession.objects.filter(holiday_closure=closure_focus)
        closure_focus_summary = {
            'closure': closure_focus,
            'closed_sessions_count': closed_sessions_qs.count(),
            'affected_bookings_count': Booking.objects.filter(
                session__holiday_closure=closure_focus,
                status__in=Booking.active_statuses(),
            ).count(),
            'generated_recoveries_count': RecoveryCredit.objects.filter(
                source=RecoveryCreditSource.HOLIDAY_CLOSURE,
                origin_session__holiday_closure=closure_focus,
            ).count(),
        }

    return {
        'staff_agenda_anchor_date': anchor_date,
        'staff_agenda_window_end': window_end,
        'staff_agenda_window_days': STAFF_AGENDA_WINDOW_DAYS,
        'staff_agenda_section_id': section_id,
        'staff_agenda_active_section': active_section,
        'staff_agenda_sections': Section.objects.filter(is_active=True).order_by('name'),
        'staff_agenda_groups': grouped_sessions,
        'staff_agenda_sessions_count': len(sessions),
        'staff_agenda_closed_sessions_count': sum(1 for session in sessions if session.status == SessionStatus.HOLIDAY_CLOSED),
        'staff_agenda_booked_count': sum(session.booked_count for session in sessions),
        'staff_agenda_closures': closures,
        'staff_recent_closures': recent_closures,
        'staff_holiday_closure_form': closure_form,
        'staff_closure_focus_summary': closure_focus_summary,
    }


def _build_staff_class_session_detail_context(session, *, date='', section=''):
    requested_date = _parse_staff_agenda_date(date) if date else session.date
    requested_section = str(section or '').strip()
    if requested_section and requested_section != str(session.section_id):
        requested_section = ''

    active_bookings = list(
        Booking.objects.select_related('student', 'used_recovery_credit', 'used_recovery_credit__origin_session')
        .filter(session=session, status=BookingStatus.BOOKED)
        .order_by('student__last_name', 'student__first_name', 'student__email')
    )
    recent_booking_events = list(
        Booking.objects.select_related('student', 'used_recovery_credit', 'used_recovery_credit__origin_session')
        .filter(session=session)
        .exclude(status=BookingStatus.BOOKED)
        .order_by('-updated_at', 'student__last_name', 'student__first_name')[:5]
    )

    booked_count = len(active_bookings)
    available_spots = max(session.capacity - booked_count, 0)
    makeup_bookings_count = sum(1 for booking in active_bookings if booking.used_recovery_credit_id)
    occupancy_percent = int((booked_count / session.capacity) * 100) if session.capacity else 0
    generated_recovery_credits_count = RecoveryCredit.objects.filter(
        origin_session=session,
        source=RecoveryCreditSource.HOLIDAY_CLOSURE,
    ).count()
    holiday_closure_affected_bookings_count = 0
    if session.holiday_closure_id:
        holiday_closure_affected_bookings_count = Booking.objects.filter(
            session=session,
            status__in=Booking.active_statuses(),
        ).count()

    if session.status == SessionStatus.HOLIDAY_CLOSED:
        summary_text = 'Sesion cerrada por feriado. No admite nuevas reservas y las recuperaciones se trazan desde el cierre asociado.'
    elif session.status == SessionStatus.CANCELLED:
        summary_text = 'Sesion cancelada. Conviene revisar solo el historial de reservas ya cargadas y cualquier accion posterior fuera de esta pantalla.'
    elif booked_count >= session.capacity:
        summary_text = 'Sesion completa en este momento. Ya no quedan cupos libres dentro de la capacidad definida.'
    elif booked_count == 0:
        summary_text = 'Sesion abierta y sin ocupacion actual. Queda lista para tomar reservas nuevas dentro de la agenda staff.'
    else:
        summary_text = f'Sesion programada con {booked_count} reserva(s) activa(s) y {available_spots} lugar(es) libre(s).'

    return {
        'staff_session': session,
        'staff_session_back_url': _build_staff_class_agenda_url(date=requested_date, section=requested_section),
        'staff_session_back_date': requested_date,
        'staff_session_back_section_id': requested_section,
        'staff_session_active_bookings': active_bookings,
        'staff_session_recent_booking_events': recent_booking_events,
        'staff_session_booked_count': booked_count,
        'staff_session_available_spots': available_spots,
        'staff_session_makeup_bookings_count': makeup_bookings_count,
        'staff_session_regular_bookings_count': booked_count - makeup_bookings_count,
        'staff_session_occupancy_percent': occupancy_percent,
        'staff_session_generated_recovery_credits_count': generated_recovery_credits_count,
        'staff_session_holiday_closure_affected_bookings_count': holiday_closure_affected_bookings_count,
        'staff_session_summary_text': summary_text,
        'staff_session_total_movements_count': booked_count + len(recent_booking_events),
    }


def _get_admin_student_detail_context(student, *, query='', manual_recovery_form=None):
    today = timezone.localdate()
    current_month = normalize_month_start(today)
    current_access = student.get_monthly_access_for(today)
    status_badges = _build_admin_status_badges(current_access)
    relevant_credits = list(
        student.recovery_credits.select_related('section', 'origin_session')
        .exclude(status__in=[RecoveryCreditStatus.REVOKED, RecoveryCreditStatus.USED])
        .order_by('expires_at', 'created_at')
    )
    available_recovery_credits = []
    expired_recovery_credits = []
    for credit in relevant_credits:
        if credit.is_expired(on_date=today):
            expired_recovery_credits.append(credit)
        else:
            available_recovery_credits.append(credit)

    upcoming_bookings = list(
        Booking.objects.select_related('session', 'session__section', 'used_recovery_credit')
        .filter(student=student, status=BookingStatus.BOOKED, session__date__gte=today)
        .order_by('session__date', 'session__start_time')[:ADMIN_DETAIL_PREVIEW_LIMIT]
    )
    recent_bookings = list(
        Booking.objects.select_related('session', 'session__section', 'used_recovery_credit')
        .filter(student=student)
        .order_by('-updated_at', '-session__date', '-session__start_time')[:ADMIN_DETAIL_PREVIEW_LIMIT]
    )
    recent_access_history = list(student.monthly_access_statuses.order_by('-month')[:3])
    relevant_recovery_credit_ids = list(student.recovery_credits.values_list('pk', flat=True))
    recent_access_ids = [access.pk for access in recent_access_history]
    if current_access is not None:
        recent_access_ids.append(current_access.pk)
    recent_audit_logs = list(
        AuditLog.objects.select_related('actor')
        .filter(
            Q(entity_type='RecoveryCredit', entity_id__in=relevant_recovery_credit_ids)
            | Q(entity_type='MonthlyAccessStatus', entity_id__in=recent_access_ids)
        )
        .order_by('-created_at')[:ADMIN_DETAIL_PREVIEW_LIMIT]
    )
    recent_window_start = today - timedelta(days=30)

    return {
        'admin_detail_student': student,
        'admin_detail_query': query,
        'admin_detail_back_url': _build_admin_redirect_url(query=query),
        'admin_detail_current_month': current_month,
        'admin_detail_current_month_label': current_month.strftime('%m/%Y'),
        'admin_detail_current_access': current_access,
        'admin_detail_section_name': student.primary_section.name if student.primary_section_id else 'Sin seccion principal',
        'admin_detail_upcoming_bookings': upcoming_bookings,
        'admin_detail_available_recoveries': available_recovery_credits,
        'admin_detail_expired_recoveries': expired_recovery_credits,
        'admin_detail_recent_bookings': recent_bookings,
        'admin_detail_recent_access_history': recent_access_history,
        'admin_detail_recent_audit_logs': recent_audit_logs,
        'admin_detail_summary': {
            'upcoming_bookings_count': len(upcoming_bookings),
            'available_recoveries_count': len(available_recovery_credits),
            'expired_recoveries_count': len(expired_recovery_credits),
            'recent_activity_count': Booking.objects.filter(student=student, updated_at__date__gte=recent_window_start).count(),
        },
        'admin_detail_manual_recovery_form': manual_recovery_form or StaffManualRecoveryCreditForm(student=student),
        **status_badges,
    }


def _build_operational_status(user, target_date):
    access = user.get_monthly_access_for(target_date)

    if user.primary_section_id is None:
        return {
            'title': 'Sin actividad asignada',
            'message': 'Todavia no tenes una actividad principal configurada. Contactanos para habilitar tu agenda.',
            'tone': 'warning',
            'can_operate': False,
        }

    if access is None:
        return {
            'title': 'Sin acceso operativo cargado',
            'message': 'Este mes todavia no tiene un estado operativo confirmado. Escribinos para revisar tu acceso.',
            'tone': 'warning',
            'can_operate': False,
        }

    if access.grants_operational_booking_access():
        return {
            'title': 'Acceso operativo activo',
            'message': 'Tu actividad de este mes esta habilitada para ver agenda y gestionar tus proximos turnos.',
            'tone': 'success',
            'can_operate': True,
        }

    if access.status == MonthlyAccessStatusType.PENDING_PAYMENT:
        return {
            'title': 'Mes pendiente de pago',
            'message': 'Tu acceso operativo de este mes esta pausado hasta registrar el pago. La agenda sigue visible, pero las acciones quedan bloqueadas.',
            'tone': 'danger',
            'can_operate': False,
        }

    if access.status == MonthlyAccessStatusType.SUSPENDED:
        return {
            'title': 'Acceso operativo suspendido',
            'message': 'Este mes no tenes acceso operativo para reservar o mover turnos. Si necesitabas operar, contactanos.',
            'tone': 'danger',
            'can_operate': False,
        }

    return {
        'title': 'Acceso operativo no disponible',
        'message': 'Tu estado actual no permite operar turnos desde la web en este momento.',
        'tone': 'warning',
        'can_operate': False,
    }


def _get_student_portal_context(user):
    now = timezone.now()
    today = timezone.localdate()
    upcoming_bookings = list(
        Booking.objects.select_related('session', 'session__section', 'used_recovery_credit')
        .filter(student=user, status=BookingStatus.BOOKED, session__date__gte=today)
        .order_by('session__date', 'session__start_time')
    )
    upcoming_booking_cards = []
    for booking in upcoming_bookings:
        can_cancel = booking.remaining_time_until_start(when=now) > Booking.SELF_SERVICE_CANCELLATION_WINDOW
        if can_cancel:
            cancel_action = {
                'can_cancel': True,
                'label': 'Cancelar turno',
                'message': 'Si cambias de plan, podes cancelarlo desde aca y el dominio resuelve la recuperacion cuando corresponde.',
                'tone': 'ready',
            }
        else:
            cancel_action = {
                'can_cancel': False,
                'label': 'Ventana cerrada',
                'message': 'La auto-cancelacion web queda disponible solo hasta 2 horas antes del inicio.',
                'tone': 'blocked',
            }
        upcoming_booking_cards.append({'booking': booking, 'cancel_action': cancel_action})

    booked_session_ids = {booking.session_id for booking in upcoming_bookings}
    section = user.primary_section
    upcoming_sessions = []

    if section is not None:
        upcoming_sessions = list(
            ClassSession.objects.select_related('section')
            .filter(section=section, date__gte=today, status=SessionStatus.SCHEDULED)
            .annotate(
                booked_count=Count(
                    'bookings',
                    filter=Q(bookings__status=BookingStatus.BOOKED),
                    distinct=True,
                )
            )
            .order_by('date', 'start_time')[:STUDENT_PORTAL_PREVIEW_LIMIT]
        )

    recovery_credits = list(
        user.recovery_credits.select_related('section', 'origin_session')
        .exclude(status__in=[RecoveryCreditStatus.REVOKED, RecoveryCreditStatus.USED])
        .order_by('expires_at', 'created_at')
    )
    available_recovery_credits = []
    expired_recovery_credits = []
    for credit in recovery_credits:
        if credit.is_expired(on_date=today):
            expired_recovery_credits.append(credit)
        else:
            available_recovery_credits.append(credit)

    recovery_credit_cards = []
    available_recovery_credit_ids_by_section = {}
    available_recovery_credit_map = {}
    for credit in available_recovery_credits:
        available_recovery_credit_map[credit.id] = credit
        available_recovery_credit_ids_by_section.setdefault(credit.section_id, []).append(credit.id)
        recovery_credit_cards.append(
            {
                'credit': credit,
                'use_url': reverse('use-recovery', args=[credit.pk]),
            }
        )

    operational_status = _build_operational_status(user, today)
    upcoming_session_cards = []
    for session in upcoming_sessions:
        action = _build_session_action(user=user, session=session)
        compatible_credit_ids = []
        for credit_id in available_recovery_credit_ids_by_section.get(session.section_id, []):
            credit = available_recovery_credit_map.get(credit_id)
            if credit and _booking_preview_is_valid(user=user, session=session, recovery_credit=credit):
                compatible_credit_ids.append(credit.id)

        upcoming_session_cards.append(
            {
                'session': session,
                'action': action,
                'compatible_recovery_count': len(compatible_credit_ids),
                'recovery_url': reverse('use-recovery', args=[compatible_credit_ids[0]]) if compatible_credit_ids else '',
            }
        )

    upcoming_makeup_bookings = [booking for booking in upcoming_bookings if booking.used_recovery_credit_id]

    return {
        'today': today,
        'primary_section': section,
        'operational_status': operational_status,
        'upcoming_bookings': upcoming_bookings,
        'upcoming_booking_cards': upcoming_booking_cards,
        'booked_session_ids': booked_session_ids,
        'upcoming_sessions': upcoming_sessions,
        'upcoming_session_cards': upcoming_session_cards,
        'available_recovery_credits': available_recovery_credits,
        'recovery_credit_cards': recovery_credit_cards,
        'upcoming_makeup_bookings_count': len(upcoming_makeup_bookings),
        'expired_recovery_credits': expired_recovery_credits,
    }


def _iter_validation_messages(exc):
    if hasattr(exc, 'message_dict'):
        for messages_list in exc.message_dict.values():
            for message in messages_list:
                yield message
        return

    if hasattr(exc, 'messages') and exc.messages:
        for message in exc.messages:
            yield message


def _translate_booking_message(message):
    return BOOKING_ERROR_MESSAGES.get(message, message)


def _booking_preview_is_valid(*, user, session, recovery_credit=None):
    booking = Booking(session=session, student=user, used_recovery_credit=recovery_credit)
    try:
        booking.full_clean()
    except ValidationError:
        return False
    return True


def _build_session_action(*, user, session, recovery_credit=None):
    booking = Booking(session=session, student=user, used_recovery_credit=recovery_credit)
    try:
        booking.full_clean()
    except ValidationError as exc:
        message = _get_booking_error_message(exc)
        if recovery_credit is None and message == 'Ya tenes una reserva activa para esta clase.':
            label = 'Reserva confirmada'
        elif recovery_credit is None and message == 'Tu acceso operativo no permite reservar esta clase en este mes.':
            label = 'Acceso no disponible'
        else:
            label = 'No disponible' if recovery_credit is None else 'No compatible'
        return {
            'can_book': False,
            'label': label,
            'message': message,
            'tone': 'blocked',
        }

    if recovery_credit is not None:
        return {
            'can_book': True,
            'label': 'Usar recuperacion',
            'message': (
                f'Esta clase es compatible con la recuperacion elegida y la reserva se registrara '
                f'como recupero de {recovery_credit.section.name}.'
            ),
            'tone': 'ready',
        }

    return {
        'can_book': True,
        'label': 'Reservar',
        'message': 'Si el horario te sirve, podes confirmar la reserva desde esta agenda.',
        'tone': 'ready',
    }


def _get_booking_error_message(exc):
    for message in _iter_validation_messages(exc):
        return _translate_booking_message(message)

    return 'No se pudo confirmar la reserva. Intenta nuevamente o escribinos si el problema sigue.'


def _get_cancellation_error_message(exc):
    if hasattr(exc, 'message_dict'):
        for messages_list in exc.message_dict.values():
            for message in messages_list:
                return CANCELLATION_ERROR_MESSAGES.get(message, message)

    if hasattr(exc, 'messages') and exc.messages:
        message = exc.messages[0]
        return CANCELLATION_ERROR_MESSAGES.get(message, message)

    return 'No se pudo cancelar la reserva. Intenta nuevamente o escribinos si el problema sigue.'


def _get_recovery_management_error_message(exc):
    if hasattr(exc, 'message_dict') and exc.message_dict:
        for messages_list in exc.message_dict.values():
            if messages_list:
                message = messages_list[0]
                return RECOVERY_MANAGEMENT_ERROR_MESSAGES.get(message, message)

    if hasattr(exc, 'messages') and exc.messages:
        message = exc.messages[0]
        return RECOVERY_MANAGEMENT_ERROR_MESSAGES.get(message, message)

    return 'No se pudo actualizar la recuperacion. Intenta nuevamente o revisalo desde admin si el problema sigue.'


def _get_safe_redirect_url(request, default_name='agenda'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return reverse(default_name)


def login_view(request):
    if request.user.is_authenticated:
        if request.user.must_change_password:
            return redirect('change-password-required')
        return redirect(_get_default_portal_url(request.user))

    form = EmailAuthenticationForm(request=request, data=request.POST or None)
    requested_next_url = request.POST.get('next') or request.GET.get('next') or ''
    next_url = ''
    if requested_next_url and url_has_allowed_host_and_scheme(requested_next_url, allowed_hosts={request.get_host()}):
        next_url = requested_next_url

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user is None:
            return render(request, 'scheduling/login.html', {'form': form, 'next': next_url})
        login(request, user)
        if user.must_change_password:
            return redirect('change-password-required')
        return redirect(next_url or _get_default_portal_url(user))

    return render(request, 'scheduling/login.html', {'form': form, 'next': next_url})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def change_password_required_view(request):
    if not request.user.must_change_password:
        return redirect(_get_default_portal_url(request.user))

    form = RequiredPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        return redirect(_get_default_portal_url(user))

    return render(request, 'scheduling/change_password_required.html', {'form': form})


@login_required
def dashboard_view(request):
    context = _get_student_portal_context(request.user)
    return render(request, 'scheduling/dashboard.html', context)


@login_required
def agenda_view(request):
    context = _get_student_portal_context(request.user)
    return render(request, 'scheduling/agenda.html', context)


@login_required
def my_bookings_view(request):
    context = _get_student_portal_context(request.user)
    return render(request, 'scheduling/my_bookings.html', context)


@login_required
def create_booking_view(request, session_id):
    if request.method != 'POST':
        return redirect('agenda')

    redirect_url = _get_safe_redirect_url(request)
    recovery_credit_id = request.POST.get('used_recovery_credit_id')

    try:
        reservation = create_booking(
            session_id=session_id,
            student=request.user,
            used_recovery_credit_id=recovery_credit_id,
        )
    except ClassSession.DoesNotExist as exc:
        raise Http404 from exc
    except ValidationError as exc:
        messages.error(request, _get_booking_error_message(exc))
    else:
        session = reservation.session
        if reservation.recovery_credit is not None:
            messages.success(
                request,
                (
                    f'Reservaste {session.section.name} del {session.date:%d/%m} a las {session.start_time:%H:%M} '
                    f'usando tu recuperacion disponible.'
                ),
            )
        else:
            messages.success(
                request,
                f'Reservaste {session.section.name} del {session.date:%d/%m} a las {session.start_time:%H:%M}.',
            )

    return redirect(redirect_url)


@login_required
def use_recovery_view(request, recovery_credit_id):
    context = _get_student_portal_context(request.user)
    credit = get_object_or_404(
        RecoveryCredit.objects.select_related('section', 'origin_session'),
        pk=recovery_credit_id,
        student=request.user,
    )
    today = context['today']
    if credit.status != RecoveryCreditStatus.AVAILABLE or credit.is_expired(on_date=today):
        messages.error(
            request,
            'La recuperacion elegida ya no esta disponible para usar. Revisa en mis turnos las recuperaciones vigentes.',
        )
        return redirect('my-bookings')

    candidate_sessions = list(
        ClassSession.objects.select_related('section')
        .filter(section=credit.section, date__gte=today, status=SessionStatus.SCHEDULED)
        .annotate(
            booked_count=Count(
                'bookings',
                filter=Q(bookings__status=BookingStatus.BOOKED),
                distinct=True,
            )
        )
        .order_by('date', 'start_time')
    )

    recovery_session_cards = []
    eligible_sessions_count = 0
    for session in candidate_sessions:
        action = _build_session_action(user=request.user, session=session, recovery_credit=credit)
        if action['can_book']:
            eligible_sessions_count += 1
        recovery_session_cards.append({'session': session, 'action': action})

    context.update(
        {
            'recovery_focus_credit': credit,
            'recovery_focus_credit_overdue': credit.is_expired(on_date=today),
            'recovery_session_cards': recovery_session_cards,
            'eligible_sessions_count': eligible_sessions_count,
        }
    )
    return render(request, 'scheduling/use_recovery.html', context)


@login_required
def cancel_booking_view(request, booking_id):
    if request.method != 'POST':
        return redirect('my-bookings')

    redirect_url = _get_safe_redirect_url(request, default_name='my-bookings')

    try:
        cancellation = cancel_booking(booking_id=booking_id, student=request.user, actor=request.user)
    except Booking.DoesNotExist as exc:
        raise Http404 from exc
    except ValidationError as exc:
        messages.error(request, _get_cancellation_error_message(exc))
    else:
        booking = cancellation.booking
        recovery_credit = cancellation.recovery_credit
        messages.success(
            request,
            (
                f'Cancelaste {booking.session.section.name} del {booking.session.date:%d/%m} '
                f'a las {booking.session.start_time:%H:%M}. '
                f'Se genero una recuperacion disponible hasta el {recovery_credit.expires_at:%d/%m/%Y}.'
            ),
        )

    return redirect(redirect_url)


@staff_required
def admin_student_list_view(request):
    query = request.GET.get('q', '').strip()
    context = _get_admin_students_context(query=query)
    return render(request, 'scheduling/admin_student_list.html', context)


@staff_required
def admin_class_agenda_view(request):
    context = _build_staff_class_agenda_context(data=request.GET)
    return render(request, 'scheduling/admin_class_agenda.html', context)


@staff_required
def admin_class_session_detail_view(request, session_id):
    session = get_object_or_404(ClassSession.objects.select_related('section', 'holiday_closure'), pk=session_id)
    context = _build_staff_class_session_detail_context(
        session,
        date=request.GET.get('date', '').strip(),
        section=request.GET.get('section', '').strip(),
    )
    return render(request, 'scheduling/admin_class_session_detail.html', context)


@staff_required
def admin_create_holiday_closure_view(request):
    if request.method != 'POST':
        return redirect('admin-class-agenda')

    requested_section = request.POST.get('section', '').strip()
    form = StaffHolidayClosureForm(data=request.POST)

    if form.is_valid():
        application = apply_holiday_closure(
            closure_date=form.cleaned_data['date'],
            reason=form.cleaned_data['reason'],
            notes=form.cleaned_data.get('notes', ''),
            actor=request.user,
            record_audit=True,
        )
        closure = application.closure
        result = application.result
        messages.success(
            request,
            (
                f'Se aplico el cierre del {closure.date:%d/%m/%Y}. '
                f'Sesiones cerradas: {result["updated_sessions"]}. '
                f'Recuperaciones nuevas: {result["created_credits"]}. '
                f'Recuperaciones ya existentes: {result["existing_credits"]}.'
            ),
        )
        redirect_url = f'{reverse("admin-class-agenda")}?{urlencode({"date": closure.date.isoformat(), "section": requested_section})}'
        return redirect(redirect_url)

    context = _build_staff_class_agenda_context(
        data={
            'date': request.POST.get('date'),
            'section': requested_section,
        },
        closure_form=form,
    )
    return render(request, 'scheduling/admin_class_agenda.html', context, status=200)


@staff_required
def admin_student_detail_view(request, student_id):
    query = request.GET.get('q', '').strip()
    student = get_object_or_404(User.objects.select_related('primary_section'), pk=student_id, role=UserRole.STUDENT)
    context = _get_admin_student_detail_context(student, query=query)
    return render(request, 'scheduling/admin_student_detail.html', context)


@staff_required
def admin_grant_manual_recovery_view(request, student_id):
    query = request.POST.get('q', '').strip()
    student = get_object_or_404(User.objects.select_related('primary_section'), pk=student_id, role=UserRole.STUDENT)
    redirect_url = _get_safe_redirect_url(request, default_name='admin-student-list')
    if redirect_url == reverse('admin-student-list'):
        redirect_url = _build_admin_student_detail_url(student.pk, query=query)

    if request.method != 'POST':
        return redirect(redirect_url)

    form = StaffManualRecoveryCreditForm(student=student, data=request.POST)
    if form.is_valid():
        credit = grant_manual_recovery_credit(
            student=student,
            section=form.cleaned_data['section'],
            granted_by=request.user,
            notes=form.cleaned_data.get('notes', ''),
            record_audit=True,
        )
        messages.success(
            request,
            (
                f'Se otorgo una recuperacion manual para {student.get_full_name() or student.email} '
                f'en {credit.section.name}. Queda disponible hasta el {credit.expires_at:%d/%m/%Y}.'
            ),
        )
        return redirect(redirect_url)

    context = _get_admin_student_detail_context(student, query=query, manual_recovery_form=form)
    return render(request, 'scheduling/admin_student_detail.html', context, status=200)


@staff_required
def admin_expire_recovery_credit_view(request, student_id, recovery_credit_id):
    query = request.POST.get('q', '').strip()
    student = get_object_or_404(User.objects.select_related('primary_section'), pk=student_id, role=UserRole.STUDENT)
    redirect_url = _get_safe_redirect_url(request, default_name='admin-student-list')
    if redirect_url == reverse('admin-student-list'):
        redirect_url = _build_admin_student_detail_url(student.pk, query=query)

    if request.method != 'POST':
        return redirect(redirect_url)

    credit = get_object_or_404(
        RecoveryCredit.objects.select_related('section', 'origin_session'),
        pk=recovery_credit_id,
        student=student,
    )

    try:
        expiration = expire_recovery_credit(
            credit=credit,
            actor=request.user,
            on_date=timezone.localdate(),
            record_audit=True,
        )
    except ValidationError as exc:
        messages.error(request, _get_recovery_management_error_message(exc))
    else:
        if expiration.changed:
            messages.success(
                request,
                f'Se marco como vencida la recuperacion de {student.get_full_name() or student.email} para {credit.section.name}.',
            )
        else:
            messages.success(request, 'La recuperacion ya estaba vencida.')

    return redirect(redirect_url)


@staff_required
def admin_toggle_student_access_view(request, student_id):
    if request.method != 'POST':
        return redirect('admin-student-list')

    query = request.POST.get('q', '').strip()
    redirect_url = _get_safe_redirect_url(request, default_name='admin-student-list')
    if redirect_url == reverse('admin-student-list') and query:
        redirect_url = _build_admin_redirect_url(query=query)
    student = get_object_or_404(User.objects.select_related('primary_section'), pk=student_id, role=UserRole.STUDENT)
    current_month = normalize_month_start(timezone.localdate())
    current_access = student.get_monthly_access_for(current_month)

    if current_access is not None and current_access.grants_operational_booking_access():
        change = suspend_student_monthly_access(
            student=student,
            actor=request.user,
            month=current_month,
            record_audit=True,
        )
        activated = False
    else:
        change = activate_student_monthly_access(
            student=student,
            actor=request.user,
            month=current_month,
            record_audit=True,
        )
        activated = True

    access = change.access

    if activated:
        messages.success(request, f'Se activo el acceso operativo de {student.get_full_name() or student.email} para {access.month:%m/%Y}.')
    else:
        messages.success(request, f'Se suspendio el acceso operativo de {student.get_full_name() or student.email} para {access.month:%m/%Y}.')

    return redirect(redirect_url)
