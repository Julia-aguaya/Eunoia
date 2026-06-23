from django import template


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
