import calendar
from datetime import date, datetime, timedelta
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
from .application.onboarding import create_student_self_signup
from .forms import (
    AccountProfileForm,
    EmailAuthenticationForm,
    RequiredPasswordChangeForm,
    StaffStudentMonthlyPlanForm,
    StudentSelfSignupForm,
    StaffClassSessionForm,
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
    StudentMonthlyPlan,
    User,
    UserRole,
    Weekday,
    WeeklyClassSlot,
    normalize_month_start,
    strip_legacy_userselections_notes,
)
from .use_cases import (
    activate_student_monthly_access,
    apply_holiday_closure,
    cancel_booking,
    create_booking,
    generate_class_sessions,
    grant_manual_recovery_credit,
    suspend_student_monthly_access,
)


STUDENT_PORTAL_PREVIEW_LIMIT = 6
ADMIN_DETAIL_PREVIEW_LIMIT = 5
STAFF_AGENDA_WINDOW_DAYS = 7
SPANISH_MONTH_NAMES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
}
SPANISH_WEEKDAY_SHORT = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
SPANISH_WEEKDAY_FULL = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
STAFF_PLAN_WEEKDAYS = [
    (Weekday.MONDAY, 'Lunes'),
    (Weekday.TUESDAY, 'Martes'),
    (Weekday.WEDNESDAY, 'Miércoles'),
    (Weekday.THURSDAY, 'Jueves'),
    (Weekday.FRIDAY, 'Viernes'),
]
STAFF_PLAN_WEEKDAY_LABELS = {
    **dict(STAFF_PLAN_WEEKDAYS),
    Weekday.SATURDAY: 'Sábado',
    Weekday.SUNDAY: 'Domingo',
}

BOOKING_ERROR_MESSAGES = {
    'Student must have a primary section before reserving.': 'Todavía no tenés una actividad principal configurada. Escribinos para habilitar tu agenda.',
    'Student can only reserve sessions in their primary section.': 'Esta clase corresponde a otra actividad. Solo podés reservar dentro de tu actividad principal.',
    'Student must have active monthly operational access for this session month.': 'Este mes no podés reservar esta clase desde el portal.',
    'This session is closed and cannot be booked.': 'Esta clase ya esta cerrada y no acepta nuevas reservas.',
    'This session has reached its capacity.': 'No quedan cupos disponibles para esta clase.',
    'Student already has an active booking for this session.': 'Ya tenés una reserva activa para esta clase.',
    'Student already has booking history for this fixed plan session.': 'Este turno fijo ya fue gestionado para esta clase.',
    'Recovery credit belongs to another student.': 'Esta recuperacion no pertenece a tu cuenta.',
    'Recovery credit is not compatible with this section.': 'Esta recuperación no se puede usar en esta actividad.',
    'Recovery credit must be used for another session in the same section.': 'La recuperacion solo sirve para otra clase de la misma actividad, no para la sesion original.',
    'Recovery credit is not available.': 'La recuperacion elegida ya no esta disponible para usar.',
    'Recovery credit is expired.': 'La recuperacion elegida esta vencida y ya no puede usarse.',
    'Recovery credit is not available for this student.': 'La recuperacion elegida ya no esta disponible en tu portal.',
}

CANCELLATION_ERROR_MESSAGES = {
    'Only active bookings can be cancelled.': 'Esta reserva ya no esta activa, asi que no se puede cancelar de nuevo desde la web.',
    'Self-service cancellation is only allowed more than 2 hours before class start.': 'Esta reserva ya no puede cancelarse desde la web porque faltan 2 horas o menos para la clase.',
    'Only the booking student can cancel this booking.': 'Solo podés cancelar tus propias reservas.',
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
            'action_label': 'Activar acceso del mes',
            'is_active': False,
            'summary_key': 'missing',
            'filter_key': 'pending',
        }

    if access.grants_operational_booking_access():
        return {
            'operational_label': 'Activo',
            'operational_tone': 'success',
            'payment_label': 'Al día',
            'payment_tone': 'success',
            'action_label': 'Suspender acceso',
            'is_active': True,
            'summary_key': 'active',
            'filter_key': 'active',
        }

    if access.status == MonthlyAccessStatusType.PENDING_PAYMENT:
        return {
            'operational_label': 'Pendiente',
            'operational_tone': 'warning',
            'payment_label': 'Impaga',
            'payment_tone': 'danger',
            'action_label': 'Registrar pago del mes',
            'is_active': False,
            'summary_key': 'pending',
            'filter_key': 'pending',
        }

    return {
        'operational_label': 'Bloqueado',
        'operational_tone': 'danger',
        'payment_label': 'Al día',
        'payment_tone': 'success',
        'action_label': 'Reactivar acceso',
        'is_active': False,
        'summary_key': 'suspended',
        'filter_key': 'pending',
    }


def _resolve_month_value(month_value, fallback=None):
    if hasattr(month_value, 'year') and hasattr(month_value, 'month'):
        return normalize_month_start(month_value)

    if isinstance(month_value, str):
        raw_value = month_value.strip()
        if raw_value:
            for input_format in ('%Y-%m', '%Y-%m-%d'):
                try:
                    return normalize_month_start(datetime.strptime(raw_value, input_format).date())
                except ValueError:
                    continue

    fallback_value = fallback if fallback is not None else timezone.localdate()
    return normalize_month_start(fallback_value)


def _build_admin_student_detail_url(student_id, query='', month=None, section=None):
    url = reverse('admin-student-detail', args=[student_id])
    params = {}
    if query:
        params['q'] = query
    if month:
        resolved_month = _resolve_month_value(month)
        params['month'] = resolved_month.strftime('%Y-%m')
    if section:
        params['section'] = str(section)
    if params:
        return f'{url}?{urlencode(params)}'
    return url


def _resolve_staff_plan_section(raw_value, fallback=None):
    if isinstance(raw_value, Section):
        return raw_value

    if raw_value in (None, ''):
        return fallback

    try:
        return Section.objects.filter(pk=int(raw_value), is_active=True).first() or fallback
    except (TypeError, ValueError):
        return fallback


def _get_student_activity_section(student, *, target_date):
    target_month = normalize_month_start(target_date)
    prefetched_plans = getattr(student, 'admin_effective_monthly_plans', None)
    if prefetched_plans is not None:
        for plan in prefetched_plans:
            if plan.month <= target_month and plan.section_id is not None:
                return plan.section

    effective_plan = student.get_effective_monthly_plan_for(target_date)
    if effective_plan is not None and effective_plan.section_id is not None:
        return effective_plan.section
    return student.primary_section


def _get_student_activity_label(student, *, target_date):
    section = _get_student_activity_section(student, target_date=target_date)
    if section is None:
        return 'Sin sección principal'
    return section.name


def _build_admin_student_row(student, access, *, query='', target_date=None):
    badges = _build_admin_status_badges(access)
    initials = ''.join(part[0] for part in [student.first_name, student.last_name] if part).upper()[:2] or student.email[:2].upper()
    activity_date = target_date or timezone.localdate()
    return {
        'student': student,
        'current_access': access,
        'section_name': _get_student_activity_label(student, target_date=activity_date),
        'detail_url': _build_admin_student_detail_url(student.pk, query=query),
        'initials': initials,
        **badges,
    }


def _get_admin_students_context(*, query='', status_filter='all'):
    current_month = normalize_month_start(timezone.localdate())
    students_qs = (
        User.objects.filter(role=UserRole.STUDENT)
        .select_related('primary_section')
        .prefetch_related(
            Prefetch(
                'monthly_access_statuses',
                queryset=MonthlyAccessStatus.objects.filter(month=current_month),
                to_attr='current_month_accesses',
            ),
            Prefetch(
                'monthly_plans',
                queryset=StudentMonthlyPlan.objects.select_related('section').filter(month__lte=current_month).order_by('-month'),
                to_attr='admin_effective_monthly_plans',
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
        'impaga': 0,
    }

    for student in students:
        access = student.current_month_accesses[0] if student.current_month_accesses else None
        row = _build_admin_student_row(student, access, query=query, target_date=current_month)
        summary[row['summary_key']] += 1
        if row['payment_label'] == 'Impaga':
            summary['impaga'] += 1
        rows.append(row)

    if status_filter == 'active':
        rows = [row for row in rows if row['filter_key'] == 'active']
    elif status_filter == 'pending':
        rows = [row for row in rows if row['operational_label'] in {'Pendiente', 'Sin estado cargado', 'Bloqueado'}]
    elif status_filter == 'impaga':
        rows = [row for row in rows if row['payment_label'] == 'Impaga']

    return {
        'admin_students': rows,
        'admin_query': query,
        'admin_status_filter': status_filter,
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


def _build_staff_class_agenda_context(*, data=None, closure_form=None, class_form=None):
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
    class_form = class_form or StaffClassSessionForm(initial={'date': anchor_date})
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
        'staff_class_session_form': class_form,
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
        'staff_session_is_manual': session.slot_id is None,
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
        'staff_class_session_form': StaffClassSessionForm(session_instance=session),
    }


def _get_admin_student_detail_context(student, *, query='', month=None, section=None, manual_recovery_form=None, monthly_plan_form=None):
    today = timezone.localdate()
    selected_month = _resolve_month_value(month, fallback=today)
    current_access = student.get_monthly_access_for(today)
    current_monthly_plan = student.get_effective_monthly_plan_for(selected_month)
    activity_section = _get_student_activity_section(student, target_date=selected_month)
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
    selected_section = _resolve_staff_plan_section(section, fallback=activity_section)
    resolved_monthly_plan_form = monthly_plan_form or StaffStudentMonthlyPlanForm(student=student, month=selected_month, section=selected_section)
    selected_plan_section = resolved_monthly_plan_form.selected_section

    return {
        'admin_detail_student': student,
        'admin_detail_query': query,
        'admin_detail_back_url': _build_admin_redirect_url(query=query),
        'admin_detail_current_month': selected_month,
        'admin_detail_current_month_label': selected_month.strftime('%m/%Y'),
        'admin_detail_current_month_input': selected_month.strftime('%Y-%m'),
        'admin_detail_current_access': current_access,
        'admin_detail_section_name': activity_section.name if activity_section is not None else 'Sin sección principal',
        'admin_detail_selected_plan_section_id': selected_plan_section.pk if selected_plan_section is not None else '',
        'admin_detail_selected_plan_section_name': selected_plan_section.name if selected_plan_section is not None else 'Sin actividad seleccionada',
        'admin_detail_upcoming_bookings': upcoming_bookings,
        'admin_detail_available_recoveries': available_recovery_credits,
        'admin_detail_expired_recoveries': expired_recovery_credits,
        'admin_detail_recent_bookings': recent_bookings,
        'admin_detail_recent_access_history': recent_access_history,
        'admin_detail_recent_audit_logs': recent_audit_logs,
        'admin_detail_monthly_plan': current_monthly_plan,
        'admin_detail_monthly_plan_summary': _build_monthly_plan_summary(current_monthly_plan),
        'admin_detail_monthly_plan_picker': _build_staff_monthly_plan_picker(resolved_monthly_plan_form, month=selected_month),
        'admin_detail_summary': {
            'upcoming_bookings_count': len(upcoming_bookings),
            'available_recoveries_count': len(available_recovery_credits),
            'expired_recoveries_count': len(expired_recovery_credits),
            'recent_activity_count': Booking.objects.filter(student=student, updated_at__date__gte=recent_window_start).count(),
        },
        'admin_detail_manual_recovery_form': manual_recovery_form or StaffManualRecoveryCreditForm(student=student),
        'admin_detail_monthly_plan_form': resolved_monthly_plan_form,
        **status_badges,
    }


def _build_operational_status(user, target_date):
    access = user.get_operational_monthly_access_for(target_date)
    effective_section = user.get_effective_portal_section_for(target_date)

    if effective_section is None:
        return {
            'title': 'Falta activar tu cuenta',
            'message': 'Todavía no vemos tu actividad principal en la cuenta. Escribinos y lo resolvemos para que puedas usar el portal con normalidad.',
            'tone': 'warning',
            'can_operate': False,
        }

    if access is None:
        return {
            'title': 'Estamos revisando este mes',
            'message': 'Todavía no confirmamos tu estado de este mes. Si querés revisarlo, escribinos y te ayudamos.',
            'tone': 'warning',
            'can_operate': False,
        }

    if access.grants_operational_booking_access():
        return {
            'title': 'Activa',
            'message': 'Este mes podés ver horarios, reservar y gestionar tus turnos desde el portal.',
            'tone': 'success',
            'can_operate': True,
        }

    if access.status == MonthlyAccessStatusType.PENDING_PAYMENT:
        return {
            'title': 'Impaga',
            'message': 'Tu cuenta está creada, pero todavía no está habilitada para reservar hasta validar la cuenta.',
            'tone': 'danger',
            'can_operate': False,
        }

    if access.status == MonthlyAccessStatusType.SUSPENDED:
        return {
            'title': 'Suspendida',
            'message': 'Este mes no podés reservar ni mover turnos desde el portal. Si necesitás ayuda, escribinos.',
            'tone': 'danger',
            'can_operate': False,
        }

    return {
        'title': 'Portal pausado',
        'message': 'Por ahora este mes no permite hacer cambios desde el portal.',
        'tone': 'warning',
        'can_operate': False,
    }


def _collect_effective_portal_sections(user, *, start_date, end_date):
    if end_date < start_date:
        return []

    sections = []
    seen_section_ids = set()
    day_cursor = start_date
    while day_cursor <= end_date:
        section = user.get_effective_portal_section_for(day_cursor)
        if section is not None and section.pk not in seen_section_ids:
            seen_section_ids.add(section.pk)
            sections.append(section)
        day_cursor += timedelta(days=1)
    return sections


def _ensure_generated_sessions_for_sections(*, start_date, end_date, sections):
    if end_date < start_date:
        return

    seen_codes = set()
    for section in sections:
        if section is None or section.code in seen_codes:
            continue
        seen_codes.add(section.code)
        if not WeeklyClassSlot.objects.filter(section=section, is_active=True).exists():
            continue
        generate_class_sessions(start_date=start_date, end_date=end_date, section_code=section.code)


def _ensure_student_portal_sessions(user, *, start_date, end_date):
    _ensure_generated_sessions_for_sections(
        start_date=start_date,
        end_date=end_date,
        sections=_collect_effective_portal_sections(user, start_date=start_date, end_date=end_date),
    )


def _ensure_fixed_plan_bookings(user, *, start_date, end_date):
    if end_date < start_date:
        return

    candidate_sessions = list(
        ClassSession.objects.select_related('section')
        .filter(date__range=(start_date, end_date), status=SessionStatus.SCHEDULED)
        .order_by('date', 'start_time')
    )
    if not candidate_sessions:
        return

    sessions_by_key = {
        (session.date, session.start_time, session.end_time, session.section_id): session for session in candidate_sessions
    }
    existing_bookings_by_session_id = set(
        Booking.objects.filter(student=user, session_id__in=[session.id for session in candidate_sessions]).values_list('session_id', flat=True)
    )
    plan_cache = {}
    day_cursor = start_date

    while day_cursor <= end_date:
        if not user.has_operational_booking_access_for(day_cursor):
            day_cursor += timedelta(days=1)
            continue

        month_start = normalize_month_start(day_cursor)
        if month_start not in plan_cache:
            plan_cache[month_start] = user.get_effective_monthly_plan_for(day_cursor)

        monthly_plan = plan_cache[month_start]
        if monthly_plan is None:
            day_cursor += timedelta(days=1)
            continue

        for slot in monthly_plan.get_weekly_slots():
            if not slot.is_effective_on(day_cursor):
                continue

            session = sessions_by_key.get((day_cursor, slot.start_time, slot.end_time, monthly_plan.section_id))
            if session is None or session.id in existing_bookings_by_session_id:
                continue

            try:
                Booking.objects.create_booking(session=session, student=user)
            except ValidationError:
                continue

            existing_bookings_by_session_id.add(session.id)

        day_cursor += timedelta(days=1)


def _get_student_portal_context(user):
    now = timezone.now()
    today = timezone.localdate()
    current_week_start, current_week_end, current_week_is_next = _get_current_workweek_window(today)
    _ensure_student_portal_sessions(user, start_date=current_week_start, end_date=current_week_end)
    portal_range_end = _shift_month(normalize_month_start(current_week_end), 1) - timedelta(days=1)
    _ensure_student_portal_sessions(user, start_date=today, end_date=portal_range_end)
    _ensure_fixed_plan_bookings(user, start_date=today, end_date=portal_range_end)
    section = user.get_effective_portal_section_for(today) or user.get_effective_portal_section_for(current_week_start)
    upcoming_bookings = list(
        Booking.objects.select_related('session', 'session__section', 'used_recovery_credit')
        .filter(student=user, status=BookingStatus.BOOKED, session__date__gte=today)
        .order_by('session__date', 'session__start_time')
    )
    upcoming_booking_cards = []
    for booking in upcoming_bookings:
        booking_status = _build_student_booking_status(user=user, booking=booking)
        can_cancel = booking.remaining_time_until_start(when=now) > Booking.SELF_SERVICE_CANCELLATION_WINDOW
        if can_cancel:
            cancel_action = {
                'can_cancel': True,
                'label': 'Cancelar turno',
                'message': 'Si cambiás de plan, podés cancelarlo desde acá. Si corresponde, la recuperación se genera automáticamente.',
                'tone': 'ready',
            }
        else:
            cancel_action = {
                'can_cancel': False,
                'label': 'Ventana cerrada',
                'message': 'Podes cancelar tu reserva con mas de 2 horas de anticipacion.',
                'tone': 'blocked',
            }
        upcoming_booking_cards.append(
            {
                'booking': booking,
                'cancel_action': cancel_action,
                'status_label': booking_status['label'],
                'status_tone': booking_status['tone'],
                'is_recovery': booking_status['is_recovery'],
            }
        )
    this_week_booking_cards = [
        card
        for card in upcoming_booking_cards
        if current_week_start <= card['booking'].session.date <= current_week_end
    ]
    weekly_plan_cards = _build_weekly_plan_cards(
        user=user,
        week_start=current_week_start,
        week_end=current_week_end,
        upcoming_booking_cards=upcoming_booking_cards,
    )
    if not weekly_plan_cards:
        weekly_plan_cards = [
            {
                'date': card['booking'].session.date,
                'slot': card['booking'].session.slot,
                'session': card['booking'].session,
                'booking': card['booking'],
                'cancel_action': card['cancel_action'],
                'action': None,
                'status_label': card['status_label'],
                'status_tone': card['status_tone'],
            }
            for card in this_week_booking_cards
        ]

    next_portal_turn_card = _build_next_portal_turn_card(
        upcoming_booking_cards=upcoming_booking_cards,
        weekly_plan_cards=weekly_plan_cards,
        today=today,
        current_time=timezone.localtime(now).time(),
    )
    booked_session_ids = {booking.session_id for booking in upcoming_bookings}
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
        .exclude(status=RecoveryCreditStatus.REVOKED)
        .order_by('expires_at', 'created_at')
    )
    available_recovery_credits = []
    expired_recovery_credits = []
    used_recovery_credits = []
    for credit in recovery_credits:
        if credit.status == RecoveryCreditStatus.USED:
            used_recovery_credits.append(credit)
            continue
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
    primary_recovery_credit_card = recovery_credit_cards[0] if recovery_credit_cards else None

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
        'current_week_start': current_week_start,
        'current_week_end': current_week_end,
        'portal_workweek_is_next': current_week_is_next,
        'primary_section': section,
        'operational_status': operational_status,
        'upcoming_bookings': upcoming_bookings,
        'upcoming_turns_count': len(upcoming_bookings) if upcoming_bookings else (1 if next_portal_turn_card is not None else 0),
        'next_portal_turn_card': next_portal_turn_card,
        'upcoming_booking_cards': upcoming_booking_cards,
        'this_week_booking_cards': this_week_booking_cards,
        'weekly_plan_cards': weekly_plan_cards,
        'booked_session_ids': booked_session_ids,
        'upcoming_sessions': upcoming_sessions,
        'upcoming_session_cards': upcoming_session_cards,
        'available_recovery_credits': available_recovery_credits,
        'recovery_credit_cards': recovery_credit_cards,
        'primary_recovery_credit_card': primary_recovery_credit_card,
        'upcoming_makeup_bookings_count': len(upcoming_makeup_bookings),
        'expired_recovery_credits': expired_recovery_credits,
        'used_recovery_credits': used_recovery_credits,
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


def _get_current_workweek_window(reference_date):
    if reference_date.weekday() >= 5:
        days_until_monday = (7 - reference_date.weekday()) % 7
        week_start = reference_date + timedelta(days=days_until_monday)
        week_end = week_start + timedelta(days=4)
        return week_start, week_end, True

    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end, False


def _build_monthly_plan_summary(plan):
    if plan is None:
        return None

    slots = list(plan.plan_slots.select_related('weekly_class_slot').order_by('position', 'weekly_class_slot__weekday', 'weekly_class_slot__start_time'))
    return {
        'plan': plan,
        'slots': [
            {
                'slot': plan_slot.weekly_class_slot,
                'weekday_label': STAFF_PLAN_WEEKDAY_LABELS.get(
                    plan_slot.weekly_class_slot.weekday,
                    plan_slot.weekly_class_slot.get_weekday_display(),
                ),
                'label': (
                    f'{STAFF_PLAN_WEEKDAY_LABELS.get(plan_slot.weekly_class_slot.weekday, plan_slot.weekly_class_slot.get_weekday_display())} '
                    f'{plan_slot.weekly_class_slot.start_time:%H:%M} a {plan_slot.weekly_class_slot.end_time:%H:%M}'
                ),
            }
            for plan_slot in slots
        ],
    }


def _build_student_booking_status(*, user, booking):
    matches_habitual_schedule = user.session_matches_effective_monthly_plan(booking.session)
    is_recovery = bool(booking.used_recovery_credit_id) and not matches_habitual_schedule
    return {
        'label': 'Recuperación' if is_recovery else 'Clase confirmada',
        'tone': 'warning' if is_recovery else 'default',
        'is_recovery': is_recovery,
        'matches_habitual_schedule': matches_habitual_schedule,
    }


def _build_staff_monthly_plan_picker(form, *, month):
    selected_ids = set()
    for value in form['slot_ids'].value() or []:
        try:
            selected_ids.add(int(value))
        except (TypeError, ValueError):
            continue

    slot_queryset = form.fields['slot_ids'].queryset
    slot_ids = list(slot_queryset.values_list('pk', flat=True))
    slot_availability = {slot_id: {'has_sessions': False, 'has_open_spots': False} for slot_id in slot_ids}

    month_start = _resolve_month_value(month)
    month_end = _shift_month(month_start, 1) - timedelta(days=1)
    monthly_sessions = ClassSession.objects.filter(
        slot_id__in=slot_ids,
        date__range=(month_start, month_end),
        status=SessionStatus.SCHEDULED,
    ).annotate(
        booked_count=Count(
            'bookings',
            filter=Q(bookings__status=BookingStatus.BOOKED),
            distinct=True,
        )
    )
    for session in monthly_sessions:
        state = slot_availability.get(session.slot_id)
        if state is None:
            continue
        state['has_sessions'] = True
        if session.booked_count < session.capacity:
            state['has_open_spots'] = True

    day_rows = [
        {
            'weekday': weekday,
            'label': label,
            'slots': [],
        }
        for weekday, label in STAFF_PLAN_WEEKDAYS
    ]
    day_map = {row['weekday']: row for row in day_rows}
    extra_slots = []

    for slot in slot_queryset:
        availability = slot_availability.get(slot.pk, {'has_sessions': False, 'has_open_spots': False})
        is_full = availability['has_sessions'] and not availability['has_open_spots']
        slot_card = {
            'id': slot.pk,
            'input_id': f'id_slot_ids_{slot.pk}',
            'weekday': slot.weekday,
            'weekday_label': STAFF_PLAN_WEEKDAY_LABELS.get(slot.weekday, slot.get_weekday_display()),
            'time_label': f'{slot.start_time:%H:%M} - {slot.end_time:%H:%M}',
            'is_selected': slot.pk in selected_ids,
            'is_disabled': is_full and slot.pk not in selected_ids,
            'is_full': is_full,
            'notes': strip_legacy_userselections_notes(slot.notes),
        }
        if slot.weekday in day_map:
            day_map[slot.weekday]['slots'].append(slot_card)
        else:
            extra_slots.append(slot_card)

    selected_slots = [slot for row in day_rows for slot in row['slots'] if slot['is_selected']]
    selected_slots.extend(slot for slot in extra_slots if slot['is_selected'])

    return {
        'days': day_rows,
        'extra_slots': extra_slots,
        'selected_slots': selected_slots,
        'selected_count': len(selected_slots),
        'has_choices': any(row['slots'] for row in day_rows) or bool(extra_slots),
    }


def _build_weekly_plan_cards(*, user, week_start, week_end, upcoming_booking_cards):
    month_starts = []
    day_cursor = week_start
    while day_cursor <= week_end:
        month_start = normalize_month_start(day_cursor)
        if month_start not in month_starts:
            month_starts.append(month_start)
        day_cursor += timedelta(days=1)

    effective_plans = {}
    for month_start in month_starts:
        effective_plan = user.get_effective_monthly_plan_for(month_start)
        if effective_plan is not None:
            effective_plans[month_start] = effective_plan
    if not effective_plans:
        return []

    sessions = list(
        ClassSession.objects.select_related('section')
        .filter(
            date__range=(week_start, week_end),
        )
        .order_by('date', 'start_time')
    )
    session_map = {(session.date, session.start_time, session.section_id): session for session in sessions}
    booking_card_by_session_id = {card['booking'].session_id: card for card in upcoming_booking_cards}
    cards = []

    day_cursor = week_start
    while day_cursor <= week_end:
        monthly_plan = effective_plans.get(normalize_month_start(day_cursor))
        if monthly_plan is not None:
            for slot in monthly_plan.get_weekly_slots():
                if not slot.is_effective_on(day_cursor):
                    continue

                session = session_map.get((day_cursor, slot.start_time, monthly_plan.section_id))
                booking_card = booking_card_by_session_id.get(session.id) if session is not None else None
                action = _build_session_action(user=user, session=session) if session is not None and booking_card is None else None
                status_label = 'Plan mensual'
                status_tone = 'default'
                if booking_card is not None:
                    status_label = booking_card['status_label']
                    status_tone = booking_card['status_tone']
                elif action is not None and action.get('state') == 'managed':
                    status_label = action['label']
                    status_tone = 'warning'
                cards.append(
                    {
                        'date': day_cursor,
                        'slot': slot,
                        'session': session,
                        'booking': booking_card['booking'] if booking_card is not None else None,
                        'cancel_action': booking_card['cancel_action'] if booking_card is not None else None,
                        'action': action,
                        'status_label': status_label,
                        'status_tone': status_tone,
                    }
                )
        day_cursor += timedelta(days=1)

    return cards


def _build_next_portal_turn_card(*, upcoming_booking_cards, weekly_plan_cards, today, current_time):
    if upcoming_booking_cards:
        next_booking_card = upcoming_booking_cards[0]
        booking = next_booking_card['booking']
        return {
            'date': booking.session.date,
            'slot': booking.session.slot,
            'session': booking.session,
            'booking': booking,
            'cancel_action': next_booking_card['cancel_action'],
            'action': None,
            'status_label': next_booking_card['status_label'],
            'status_tone': next_booking_card['status_tone'],
        }

    for card in weekly_plan_cards:
        start_time = card['session'].start_time if card['session'] is not None else card['slot'].start_time
        if card['date'] < today:
            continue
        if card['date'] == today and start_time <= current_time:
            continue
        return card

    return None


def _parse_agenda_month(raw_value, fallback_date):
    if not raw_value:
        return normalize_month_start(fallback_date)

    try:
        year_str, month_str = raw_value.split('-', 1)
        return date(int(year_str), int(month_str), 1)
    except (TypeError, ValueError):
        return normalize_month_start(fallback_date)


def _shift_month(month_start, delta):
    month_index = (month_start.year * 12 + month_start.month - 1) + delta
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _build_agenda_calendar_context(*, user, context, month_start):
    regular_booking_dates = set()
    makeup_booking_dates = set()
    for card in context['upcoming_booking_cards']:
        booking_date = card['booking'].session.date
        if card['is_recovery']:
            makeup_booking_dates.add(booking_date)
        else:
            regular_booking_dates.add(booking_date)
    booked_dates = regular_booking_dates | makeup_booking_dates
    monthly_plan = user.get_effective_monthly_plan_for(month_start)
    planned_dates = set()
    day_cursor = month_start
    month_end = _shift_month(month_start, 1) - timedelta(days=1)
    while day_cursor <= month_end:
        effective_plan = user.get_effective_monthly_plan_for(day_cursor)
        if effective_plan is not None:
            for slot in effective_plan.get_weekly_slots():
                if slot.is_effective_on(day_cursor):
                    planned_dates.add(day_cursor)
                    break
        day_cursor += timedelta(days=1)

    month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year, month_start.month)
    visible_range_start = month_calendar[0][0]
    visible_range_end = month_calendar[-1][-1]
    weeks = []
    for week in month_calendar:
        week_days = []
        for day in week:
            week_days.append(
                {
                    'date': day,
                    'day_number': day.day,
                    'in_month': day.month == month_start.month,
                    'has_monthly_plan': day in planned_dates,
                    'has_regular_booking': day in regular_booking_dates,
                    'has_makeup_booking': day in makeup_booking_dates,
                    'has_booking': day in booked_dates,
                    'is_today': day == context['today'],
                }
            )
        weeks.append(week_days)

    visible_booking_cards = [
        card
        for card in context['upcoming_booking_cards']
        if visible_range_start <= card['booking'].session.date <= visible_range_end
    ]

    return {
        'agenda_month_start': month_start,
        'agenda_month_label': f"{SPANISH_MONTH_NAMES[month_start.month]} {month_start.year}",
        'agenda_weekday_labels': SPANISH_WEEKDAY_FULL,
        'agenda_calendar_weeks': weeks,
        'agenda_monthly_plan_summary': _build_monthly_plan_summary(monthly_plan),
        'agenda_visible_booking_cards': visible_booking_cards,
        'agenda_visible_bookings_count': len(visible_booking_cards),
        'agenda_prev_url': f"{reverse('agenda')}?{urlencode({'month': _shift_month(month_start, -1).strftime('%Y-%m')})}",
        'agenda_next_url': f"{reverse('agenda')}?{urlencode({'month': _shift_month(month_start, 1).strftime('%Y-%m')})}",
    }


def _build_recovery_calendar_context(
    *,
    credit_id,
    recovery_session_cards,
    recovery_day_cards,
    fixed_schedule_dates,
    month_start,
    selectable_dates=None,
    selected_date=None,
    selected_session_id=None,
):
    available_dates = {card['session'].date for card in recovery_session_cards}
    published_dates = {card['session'].date for card in recovery_day_cards}
    unavailable_dates = published_dates - available_dates
    fixed_schedule_dates = set(fixed_schedule_dates)
    selectable_dates = set(selectable_dates or ()) | published_dates
    cards_by_date = {}
    for card in recovery_day_cards:
        cards_by_date.setdefault(card['session'].date, []).append(card)

    selectable_dates = sorted(selectable_dates)
    selectable_available_dates = sorted(day for day in selectable_dates if day in available_dates)
    default_selected_date = selectable_available_dates[0] if selectable_available_dates else (selectable_dates[0] if selectable_dates else None)
    selected_date = selected_date if selected_date in selectable_dates else default_selected_date

    month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year, month_start.month)
    weeks = []
    for week in month_calendar:
        week_days = []
        for day in week:
            week_days.append(
                {
                    'date': day,
                    'day_number': day.day,
                    'in_month': day.month == month_start.month,
                    'has_fixed_schedule': day in fixed_schedule_dates,
                    'has_habitual_plan': day in fixed_schedule_dates,
                    'has_availability': day in available_dates,
                    'has_available_recovery': day in available_dates,
                    'has_published_recovery': day in published_dates,
                    'has_unavailable_recovery': day in unavailable_dates,
                    'is_selectable': day in selectable_dates,
                    'is_selected': selected_date == day,
                    'select_url': (
                        f"{reverse('use-recovery', args=[credit_id])}?{urlencode({'month': month_start.strftime('%Y-%m'), 'date': day.isoformat()})}"
                        if day in selectable_dates
                        else ''
                    ),
                }
            )
        weeks.append(week_days)
    selected_day_cards = cards_by_date.get(selected_date, []) if selected_date else []
    selected_session_card = None
    for card in selected_day_cards:
        if selected_session_id and str(card['session'].id) == str(selected_session_id):
            selected_session_card = card
            break
    if selected_session_card is None and selected_day_cards:
        for card in selected_day_cards:
            if card['action']['can_book']:
                selected_session_card = card
                break

    return {
        'recovery_month_start': month_start,
        'recovery_month_label': f"{SPANISH_MONTH_NAMES[month_start.month]} {month_start.year}",
        'recovery_weekday_labels': SPANISH_WEEKDAY_FULL,
        'recovery_calendar_weeks': weeks,
        'recovery_available_dates': selectable_dates,
        'recovery_selected_date': selected_date,
        'recovery_selected_day_cards': selected_day_cards,
        'recovery_selected_session_card': selected_session_card,
        'recovery_prev_url': f"{reverse('use-recovery', args=[credit_id])}?{urlencode({'month': _shift_month(month_start, -1).strftime('%Y-%m')})}",
        'recovery_next_url': f"{reverse('use-recovery', args=[credit_id])}?{urlencode({'month': _shift_month(month_start, 1).strftime('%Y-%m')})}",
    }


def _build_recovery_session_action(*, user, session, recovery_credit, now):
    action = _build_session_action(user=user, session=session, recovery_credit=recovery_credit)
    if action['can_book'] and session.starts_at() <= now:
        return {
            'can_book': False,
            'label': 'Clase ya pasada',
            'message': 'Esta clase ya pasó y queda solo como referencia para revisar la semana.',
            'tone': 'blocked',
            'state': 'past',
        }
    return action


def _build_booking_detail_modal_context(*, request, context):
    detail_booking_id = request.GET.get('detail')
    if not detail_booking_id:
        return {
            'detail_booking_card': None,
            'detail_cancel_deadline': None,
            'detail_back_url': reverse('dashboard'),
        }

    selected_card = None
    for card in context['upcoming_booking_cards']:
        if str(card['booking'].id) == str(detail_booking_id):
            selected_card = card
            break

    if selected_card is None:
        return {
            'detail_booking_card': None,
            'detail_cancel_deadline': None,
            'detail_back_url': reverse('dashboard'),
        }

    cancel_deadline = timezone.localtime(selected_card['booking'].session.starts_at() - Booking.SELF_SERVICE_CANCELLATION_WINDOW)
    return {
        'detail_booking_card': selected_card,
        'detail_cancel_deadline': cancel_deadline,
        'detail_back_url': reverse('dashboard'),
    }


def _build_recovery_detail_modal_context(*, request, context):
    detail_credit_id = request.GET.get('credit_detail')
    if not detail_credit_id:
        return {
            'detail_recovery_credit': None,
            'detail_recovery_back_url': reverse('my-bookings'),
        }

    all_credits = context['available_recovery_credits'] + context['used_recovery_credits'] + context['expired_recovery_credits']
    selected_credit = None
    for credit in all_credits:
        if str(credit.id) == str(detail_credit_id):
            selected_credit = credit
            break

    return {
        'detail_recovery_credit': selected_credit,
        'detail_recovery_back_url': reverse('my-bookings'),
    }


def _build_session_action(*, user, session, recovery_credit=None):
    existing_booking = (
        Booking.objects.select_related('session')
        .filter(session=session, student=user)
        .order_by('-created_at', '-pk')
        .first()
    )
    if recovery_credit is None and existing_booking is not None and user.session_matches_effective_monthly_plan(session):
        history_states = {
            BookingStatus.CANCELLED: ('Turno cancelado', 'Este turno fijo ya lo cancelaste para esta clase.'),
            BookingStatus.ATTENDED: ('Clase ya tomada', 'Este turno fijo ya quedó marcado como asistido.'),
            BookingStatus.NO_SHOW: ('Clase cerrada', 'Este turno fijo ya quedó marcado como ausente.'),
            BookingStatus.MOVED: ('Turno reprogramado', 'Este turno fijo ya fue movido a otra clase.'),
        }
        label, message = history_states.get(
            existing_booking.status,
            ('Turno ya gestionado', 'Este turno fijo ya fue gestionado para esta clase.'),
        )
        return {
            'can_book': False,
            'label': label,
            'message': message,
            'tone': 'blocked',
            'state': 'managed',
        }

    booking = Booking(session=session, student=user, used_recovery_credit=recovery_credit)
    try:
        booking.full_clean()
    except ValidationError as exc:
        message = _get_booking_error_message(exc)
        if message == 'Ya tenés una reserva activa para esta clase.':
            label = 'Ya reservada'
            state = 'booked'
        elif message == 'Este turno fijo ya fue gestionado para esta clase.':
            label = 'Turno ya gestionado'
            state = 'managed'
        elif message == 'No quedan cupos disponibles para esta clase.':
            label = 'Cupo completo'
            state = 'full'
        elif recovery_credit is None and message == 'Este mes no podés reservar esta clase desde el portal.':
            label = 'Agenda cerrada este mes'
            state = 'paused'
        else:
            label = 'No disponible para reservar' if recovery_credit is None else 'No disponible para esta recuperación'
            state = 'blocked'
        return {
            'can_book': False,
            'label': label,
            'message': message,
            'tone': 'blocked',
            'state': state,
        }

    if recovery_credit is not None:
        return {
            'can_book': True,
            'label': 'Usar recuperación',
            'message': (
                f'Podés usar esta recuperación para reservar esta clase de {recovery_credit.section.name}.'
            ),
            'tone': 'ready',
            'state': 'ready',
        }

    return {
        'can_book': True,
        'label': 'Reservar',
        'message': 'Si el horario te sirve, podés confirmar la reserva desde esta agenda.',
        'tone': 'ready',
        'state': 'ready',
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


def register_view(request):
    if request.user.is_authenticated:
        if request.user.must_change_password:
            return redirect('change-password-required')
        return redirect(_get_default_portal_url(request.user))

    form = StudentSelfSignupForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = create_student_self_signup(
            email=form.cleaned_data['email'],
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
            primary_section=form.cleaned_data['primary_section'],
            phone=form.cleaned_data.get('phone', ''),
            password=form.cleaned_data['password1'],
        )
        login(request, user)
        messages.success(
            request,
            'Tu cuenta quedó creada. Tu actividad ya está registrada y el acceso se habilita cuando el pago esté validado.',
        )
        return redirect('dashboard')

    return render(request, 'scheduling/register.html', {'form': form})


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
    context.update(_build_booking_detail_modal_context(request=request, context=context))
    return render(request, 'scheduling/dashboard.html', context)


@login_required
def agenda_view(request):
    today = timezone.localdate()
    month_start = _parse_agenda_month(request.GET.get('month'), today)
    month_end = _shift_month(month_start, 1) - timedelta(days=1)
    _ensure_student_portal_sessions(request.user, start_date=month_start, end_date=month_end)
    _ensure_fixed_plan_bookings(request.user, start_date=month_start, end_date=month_end)
    context = _get_student_portal_context(request.user)
    context.update(_build_agenda_calendar_context(user=request.user, context=context, month_start=month_start))
    context.update(_build_booking_detail_modal_context(request=request, context=context))
    context['detail_back_url'] = f"{reverse('agenda')}?{urlencode({'month': month_start.strftime('%Y-%m')})}"
    return render(request, 'scheduling/agenda.html', context)


@login_required
def my_bookings_view(request):
    context = _get_student_portal_context(request.user)
    context.update(_build_recovery_detail_modal_context(request=request, context=context))
    return render(request, 'scheduling/my_bookings.html', context)


@login_required
def account_view(request):
    context = _get_student_portal_context(request.user)
    is_editing = request.method == 'POST' or request.GET.get('edit') == '1'
    form = AccountProfileForm(request.user, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Actualizamos tus datos de la cuenta.')
        return redirect('account')

    context.update(
        {
            'account_form': form,
            'account_is_editing': is_editing,
        }
    )
    return render(request, 'scheduling/account.html', context)


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

    now = timezone.localtime()
    week_start, week_end, recovery_week_is_next = _get_current_workweek_window(today)
    month_start = _parse_agenda_month(request.GET.get('month'), today)
    month_end = date(month_start.year, month_start.month, calendar.monthrange(month_start.year, month_start.month)[1])
    _ensure_generated_sessions_for_sections(
        start_date=week_start,
        end_date=week_end,
        sections=Section.objects.filter(code__in=credit.compatible_section_codes()),
    )
    fixed_schedule_dates = set()
    day_cursor = month_start
    while day_cursor <= month_end:
        effective_plan = request.user.get_effective_monthly_plan_for(day_cursor)
        if effective_plan is None:
            day_cursor += timedelta(days=1)
            continue
        for slot in effective_plan.get_weekly_slots():
            if slot.is_effective_on(day_cursor):
                fixed_schedule_dates.add(day_cursor)
                break
        day_cursor += timedelta(days=1)

    if not fixed_schedule_dates:
        fixed_schedule_dates = {
            session.date
            for session in ClassSession.objects.filter(
                section__code__in=credit.compatible_section_codes(),
                status=SessionStatus.SCHEDULED,
                date__range=(month_start, month_end),
            )
        }

    candidate_sessions = list(
        ClassSession.objects.select_related('section')
        .filter(
            section__code__in=credit.compatible_section_codes(),
            status=SessionStatus.SCHEDULED,
            date__range=(week_start, week_end),
        )
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
    recovery_day_cards = []
    for session in candidate_sessions:
        action = _build_recovery_session_action(user=request.user, session=session, recovery_credit=credit, now=now)
        if action['can_book']:
            display_label = f'{session.start_time:%H:%M}'
        elif action['state'] == 'full':
            display_label = f'{session.start_time:%H:%M} - cupo completo'
        elif action['state'] == 'booked':
            display_label = f'{session.start_time:%H:%M} - ya reservada'
        elif action['state'] == 'paused':
            display_label = f'{session.start_time:%H:%M} - agenda cerrada'
        elif action['state'] == 'past':
            display_label = f'{session.start_time:%H:%M} - ya pasó'
        else:
            display_label = f'{session.start_time:%H:%M} - no disponible'
        recovery_day_cards.append(
            {
                'session': session,
                'action': action,
                'display_label': display_label,
            }
        )
        if action['can_book']:
            recovery_session_cards.append({'session': session, 'action': action})

    recovery_selectable_dates = {
        day for day in fixed_schedule_dates if week_start <= day <= week_end
    } | {card['session'].date for card in recovery_session_cards}

    selected_date = None
    raw_date = request.GET.get('date')
    if raw_date:
        try:
            selected_date = date.fromisoformat(raw_date)
        except ValueError:
            selected_date = None
    selected_session_id = request.GET.get('session')

    recovery_calendar_context = _build_recovery_calendar_context(
        credit_id=credit.id,
        recovery_session_cards=recovery_session_cards,
        recovery_day_cards=recovery_day_cards,
        fixed_schedule_dates=fixed_schedule_dates,
        month_start=month_start,
        selectable_dates=recovery_selectable_dates,
        selected_date=selected_date,
        selected_session_id=selected_session_id,
    )

    context.update(
        {
            'recovery_focus_credit': credit,
            'recovery_focus_credit_overdue': credit.is_expired(on_date=today),
            'recovery_session_cards': recovery_session_cards,
            'recovery_day_cards': recovery_day_cards,
            'eligible_sessions_count': len(recovery_session_cards),
            'recovery_week_start': week_start,
            'recovery_week_end': week_end,
            'recovery_workweek_is_next': recovery_week_is_next,
            'recovery_month_end': month_end,
            **recovery_calendar_context,
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
    status_filter = request.GET.get('status', 'all').strip() or 'all'
    context = _get_admin_students_context(query=query, status_filter=status_filter)
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
def admin_update_class_session_view(request, session_id):
    session = get_object_or_404(ClassSession.objects.select_related('section', 'holiday_closure', 'slot'), pk=session_id)
    if request.method != 'POST':
        return redirect('admin-class-session-detail', session_id=session.pk)

    if session.slot_id is not None:
        messages.error(request, 'Solo podés editar clases creadas manualmente desde el admin.')
        return redirect('admin-class-session-detail', session_id=session.pk)

    form = StaffClassSessionForm(data=request.POST, session_instance=session)
    if form.is_valid():
        updated_session = form.save()
        messages.success(
            request,
            (
                f'Se actualizó la clase de {updated_session.section.name} del {updated_session.date:%d/%m/%Y} '
                f'de {updated_session.start_time:%H:%M} a {updated_session.end_time:%H:%M}.'
            ),
        )
        return redirect('admin-class-session-detail', session_id=updated_session.pk)

    context = _build_staff_class_session_detail_context(
        session,
        date=request.GET.get('date', '').strip(),
        section=request.GET.get('section', '').strip(),
    )
    context['staff_class_session_form'] = form
    return render(request, 'scheduling/admin_class_session_detail.html', context, status=200)


@staff_required
def admin_delete_class_session_view(request, session_id):
    session = get_object_or_404(ClassSession.objects.select_related('section', 'slot'), pk=session_id)
    if request.method != 'POST':
        return redirect('admin-class-session-detail', session_id=session.pk)

    if session.slot_id is not None:
        messages.error(request, 'Solo podés eliminar clases creadas manualmente desde el admin.')
        return redirect('admin-class-session-detail', session_id=session.pk)

    if session.bookings.exists():
        messages.error(request, 'No podés eliminar una clase que ya tiene reservas asociadas.')
        return redirect('admin-class-session-detail', session_id=session.pk)

    section_name = session.section.name
    session_date = session.date
    start_time = session.start_time
    session.delete()
    messages.success(
        request,
        f'Se eliminó la clase de {section_name} del {session_date:%d/%m/%Y} a las {start_time:%H:%M}.',
    )
    return redirect(_build_staff_class_agenda_url(date=session_date, section=''))


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
def admin_create_class_session_view(request):
    if request.method != 'POST':
        return redirect('admin-class-agenda')

    form = StaffClassSessionForm(data=request.POST)
    requested_section = request.POST.get('section_filter', '').strip()

    if form.is_valid():
        session = form.save()
        messages.success(
            request,
            (
                f'Se creó la clase de {session.section.name} del {session.date:%d/%m/%Y} '
                f'de {session.start_time:%H:%M} a {session.end_time:%H:%M}.'
            ),
        )
        redirect_url = f'{reverse("admin-class-agenda")}?{urlencode({"date": session.date.isoformat(), "section": session.section_id})}'
        return redirect(redirect_url)

    context = _build_staff_class_agenda_context(
        data={
            'date': request.POST.get('date') or timezone.localdate().isoformat(),
            'section': requested_section,
        },
        class_form=form,
    )
    return render(request, 'scheduling/admin_class_agenda.html', context, status=200)


@staff_required
def admin_student_detail_view(request, student_id):
    query = request.GET.get('q', '').strip()
    selected_month = _resolve_month_value(request.GET.get('month'), fallback=timezone.localdate())
    selected_section = request.GET.get('section')
    student = get_object_or_404(User.objects.select_related('primary_section'), pk=student_id, role=UserRole.STUDENT)
    context = _get_admin_student_detail_context(student, query=query, month=selected_month, section=selected_section)
    return render(request, 'scheduling/admin_student_detail.html', context)


@staff_required
def admin_update_student_monthly_plan_view(request, student_id):
    query = request.POST.get('q', '').strip()
    selected_month = _resolve_month_value(request.POST.get('month'), fallback=timezone.localdate())
    selected_section = request.POST.get('section')
    student = get_object_or_404(User.objects.select_related('primary_section'), pk=student_id, role=UserRole.STUDENT)
    redirect_url = _get_safe_redirect_url(request, default_name='admin-student-list')
    if redirect_url == reverse('admin-student-list'):
        redirect_url = _build_admin_student_detail_url(student.pk, query=query, month=selected_month, section=selected_section)

    if request.method != 'POST':
        return redirect(redirect_url)

    form = StaffStudentMonthlyPlanForm(student=student, month=selected_month, section=_resolve_staff_plan_section(selected_section), data=request.POST)
    if form.is_valid():
        plan = form.save()
        messages.success(
            request,
            (
                f'Se actualizó el plan mensual de {student.get_full_name() or student.email} '
                f'para {plan.month:%m/%Y} con {plan.plan_slots.count()} horario(s) fijo(s).'
            ),
        )
        return redirect(redirect_url)

    context = _get_admin_student_detail_context(student, query=query, month=selected_month, section=selected_section, monthly_plan_form=form)
    return render(request, 'scheduling/admin_student_detail.html', context, status=200)


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
def admin_mark_student_paid_view(request, student_id):
    if request.method != 'POST':
        return redirect('admin-student-list')

    query = request.POST.get('q', '').strip()
    redirect_url = _get_safe_redirect_url(request, default_name='admin-student-list')
    if redirect_url == reverse('admin-student-list') and query:
        redirect_url = _build_admin_redirect_url(query=query)

    student = get_object_or_404(User.objects.select_related('primary_section'), pk=student_id, role=UserRole.STUDENT)
    current_month = normalize_month_start(timezone.localdate())
    change = activate_student_monthly_access(
        student=student,
        actor=request.user,
        month=current_month,
        record_audit=True,
    )

    messages.success(
        request,
        f'Se registró el pago de {student.get_full_name() or student.email} y el acceso quedó activo para {change.access.month:%m/%Y}.',
    )
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
