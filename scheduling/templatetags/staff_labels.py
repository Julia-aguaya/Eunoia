from django import template

from scheduling.models import strip_hidden_recovery_credit_notes


WEEKDAY_LABELS = {
    0: 'Lunes',
    1: 'Martes',
    2: 'Miércoles',
    3: 'Jueves',
    4: 'Viernes',
    5: 'Sábado',
    6: 'Domingo',
}

WEEKDAY_SHORT_LABELS = {
    0: 'Lun',
    1: 'Mar',
    2: 'Mié',
    3: 'Jue',
    4: 'Vie',
    5: 'Sáb',
    6: 'Dom',
}

MONTH_LABELS = {
    1: 'enero',
    2: 'febrero',
    3: 'marzo',
    4: 'abril',
    5: 'mayo',
    6: 'junio',
    7: 'julio',
    8: 'agosto',
    9: 'septiembre',
    10: 'octubre',
    11: 'noviembre',
    12: 'diciembre',
}


register = template.Library()


SESSION_STATUS_LABELS = {
    'scheduled': 'Programada',
    'cancelled': 'Cancelada',
    'holiday_closed': 'Cerrada por feriado',
}


BOOKING_STATUS_LABELS = {
    'booked': 'Activa',
    'cancelled': 'Cancelada',
    'attended': 'Asistio',
    'no_show': 'Ausente',
    'moved': 'Reprogramada',
}


RECOVERY_SOURCE_LABELS = {
    'timely_cancellation': 'cancelacion a tiempo',
    'holiday_closure': 'cierre por feriado',
    'session_cancellation': 'cancelacion de clase',
    'manual': 'carga manual',
}


@register.filter(name='staff_session_status_label')
@register.filter(name='session_status_label')
def staff_session_status_label(value):
    return SESSION_STATUS_LABELS.get(value, value)


@register.filter(name='staff_booking_status_label')
@register.filter(name='booking_status_label')
def staff_booking_status_label(value):
    return BOOKING_STATUS_LABELS.get(value, value)


@register.filter(name='staff_recovery_source_label')
@register.filter(name='recovery_source_label')
def staff_recovery_source_label(value):
    return RECOVERY_SOURCE_LABELS.get(value, value)


@register.filter(name='staff_recovery_notes_public')
@register.filter(name='recovery_notes_public')
def staff_recovery_notes_public(value):
    return strip_hidden_recovery_credit_notes(value)


@register.filter(name='weekday_spanish')
def weekday_spanish(value):
    weekday = getattr(value, 'weekday', None)
    if callable(weekday):
        weekday_index = weekday()
        if isinstance(weekday_index, int):
            return WEEKDAY_LABELS.get(weekday_index, value)
    return value


@register.filter(name='weekday_short_spanish')
def weekday_short_spanish(value):
    weekday = getattr(value, 'weekday', None)
    if callable(weekday):
        weekday_index = weekday()
        if isinstance(weekday_index, int):
            return WEEKDAY_SHORT_LABELS.get(weekday_index, value)
    return value


@register.filter(name='short_day_month_spanish')
def short_day_month_spanish(value):
    weekday = weekday_short_spanish(value)
    day = getattr(value, 'day', None)
    month = getattr(value, 'month', None)
    if day is None or month is None:
        return value
    return f'{weekday} {day:02d}/{month:02d}'


@register.filter(name='full_day_month_spanish')
def full_day_month_spanish(value):
    weekday = weekday_spanish(value)
    day = getattr(value, 'day', None)
    month = getattr(value, 'month', None)
    if day is None or month is None:
        return value
    return f'{weekday} {day:02d}/{month:02d}'


@register.filter(name='long_date_spanish')
def long_date_spanish(value):
    weekday = weekday_spanish(value)
    day = getattr(value, 'day', None)
    month = getattr(value, 'month', None)
    if day is None or month is None:
        return value
    return f'{weekday} {day} de {MONTH_LABELS.get(month, month)}'
