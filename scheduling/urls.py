from django.urls import path

from .views import (
    admin_class_agenda_view,
    admin_class_session_detail_view,
    admin_create_holiday_closure_view,
    admin_student_detail_view,
    admin_expire_recovery_credit_view,
    admin_grant_manual_recovery_view,
    admin_student_list_view,
    admin_toggle_student_access_view,
    agenda_view,
    cancel_booking_view,
    change_password_required_view,
    create_booking_view,
    dashboard_view,
    login_view,
    logout_view,
    my_bookings_view,
    use_recovery_view,
)


urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('staff/', admin_student_list_view, name='admin-student-list'),
    path('staff/clases/', admin_class_agenda_view, name='admin-class-agenda'),
    path('staff/clases/<int:session_id>/', admin_class_session_detail_view, name='admin-class-session-detail'),
    path('staff/feriados/crear/', admin_create_holiday_closure_view, name='admin-create-holiday-closure'),
    path('staff/alumnas/<int:student_id>/', admin_student_detail_view, name='admin-student-detail'),
    path(
        'staff/alumnas/<int:student_id>/recuperaciones/otorgar/',
        admin_grant_manual_recovery_view,
        name='admin-grant-manual-recovery',
    ),
    path(
        'staff/alumnas/<int:student_id>/recuperaciones/<int:recovery_credit_id>/expire/',
        admin_expire_recovery_credit_view,
        name='admin-expire-recovery-credit',
    ),
    path(
        'staff/alumnas/<int:student_id>/toggle-access/',
        admin_toggle_student_access_view,
        name='admin-toggle-student-access',
    ),
    path('agenda/', agenda_view, name='agenda'),
    path('agenda/<int:session_id>/reservar/', create_booking_view, name='create-booking'),
    path('recuperaciones/<int:recovery_credit_id>/usar/', use_recovery_view, name='use-recovery'),
    path('mis-turnos/', my_bookings_view, name='my-bookings'),
    path('mis-turnos/<int:booking_id>/cancelar/', cancel_booking_view, name='cancel-booking'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('change-password-required/', change_password_required_view, name='change-password-required'),
]
