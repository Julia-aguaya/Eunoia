from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from io import StringIO

from django.db import transaction
from django.utils import timezone

from scheduling.bootstrap import ensure_demo_slots, ensure_sections, ensure_staff_user, generate_upcoming_sessions
from scheduling.models import (
    Booking,
    ClassSession,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    RecoveryCredit,
    Section,
    SessionStatus,
    User,
)
from scheduling.student_import import import_students_from_csv
from scheduling.use_cases import (
    activate_student_monthly_access,
    cancel_booking,
    create_booking,
    suspend_student_monthly_access,
)


DEMO_ADMIN_EMAIL = 'admin.demo@example.com'
DEMO_ADMIN_PASSWORD = 'DemoAdmin2026!'
DEMO_STAFF_EMAIL = 'staff.demo@example.com'
DEMO_STAFF_PASSWORD = 'DemoStaff2026!'
DEMO_STUDENT_PASSWORD = 'DemoStudent2026!'
DEMO_SESSION_WINDOW_DAYS = 28

DEMO_STUDENTS = (
    {
        'email': 'ada.demo@example.com',
        'first_name': 'Ada',
        'last_name': 'Lovelace',
        'primary_section': 'reformer_arriba',
        'phone': '1100-0001',
        'notes': 'Demo activa con una reserva futura.',
    },
    {
        'email': 'bea.demo@example.com',
        'first_name': 'Bea',
        'last_name': 'Hamilton',
        'primary_section': 'reformer_abajo',
        'phone': '1100-0002',
        'notes': 'Demo impaga para mostrar bloqueo operativo.',
    },
    {
        'email': 'clara.demo@example.com',
        'first_name': 'Clara',
        'last_name': 'Schumann',
        'primary_section': 'cadillac',
        'phone': '1100-0003',
        'notes': 'Demo suspendida para mostrar estado no operativo.',
    },
    {
        'email': 'dora.demo@example.com',
        'first_name': 'Dora',
        'last_name': 'Maar',
        'primary_section': 'cadillac',
        'phone': '1100-0004',
        'notes': 'Demo con recuperacion ya usada en una reserva futura.',
    },
    {
        'email': 'eva.demo@example.com',
        'first_name': 'Eva',
        'last_name': 'Peron',
        'primary_section': 'reformer_arriba',
        'phone': '1100-0005',
        'notes': 'Demo con recuperacion disponible generada por cancelacion.',
    },
    {
        'email': 'sofia.demo@example.com',
        'first_name': 'Sofia',
        'last_name': 'Kovalevskaya',
        'primary_section': 'reformer_abajo',
        'phone': '1100-0006',
        'notes': 'Demo limpia para correr el smoke test end-to-end.',
    },
)

ACTIVE_DEMO_STUDENT_EMAILS = {
    'ada.demo@example.com',
    'dora.demo@example.com',
    'eva.demo@example.com',
    'sofia.demo@example.com',
}
PENDING_DEMO_STUDENT_EMAILS = {'bea.demo@example.com'}
SUSPENDED_DEMO_STUDENT_EMAILS = {'clara.demo@example.com'}


@dataclass(frozen=True)
class DemoSeedSummary:
    sections_ensured: int
    sections_created: int
    demo_slots_created: int
    sessions_generated: int
    students_seeded: int
    bookings_created: int
    recoveries_created: int


def seed_demo_environment():
    ensured_sections, created_sections = ensure_sections()
    admin_result = ensure_staff_user(
        email=DEMO_ADMIN_EMAIL,
        password=DEMO_ADMIN_PASSWORD,
        first_name='Admin',
        last_name='Demo',
        reset_password=True,
        is_superuser=True,
    )
    ensure_staff_user(
        email=DEMO_STAFF_EMAIL,
        password=DEMO_STAFF_PASSWORD,
        first_name='Staff',
        last_name='Demo',
        reset_password=True,
        is_superuser=False,
    )
    demo_slots_created = ensure_demo_slots(notes='Starter schedule created by seed_demo_eunoia.')
    sessions_generated = generate_upcoming_sessions(DEMO_SESSION_WINDOW_DAYS)

    students = _recreate_demo_students()
    _seed_monthly_access_statuses(students)
    seeded_entities = _seed_demo_bookings_and_recoveries(students, admin_result.user)

    return DemoSeedSummary(
        sections_ensured=ensured_sections,
        sections_created=created_sections,
        demo_slots_created=demo_slots_created,
        sessions_generated=sessions_generated,
        students_seeded=len(students),
        bookings_created=seeded_entities['bookings_created'],
        recoveries_created=seeded_entities['recoveries_created'],
    )


def _recreate_demo_students():
    demo_emails = [student['email'] for student in DEMO_STUDENTS]
    User.objects.filter(email__in=demo_emails).delete()

    csv_content = StringIO()
    csv_content.write(
        'email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes\n'
    )
    for student in DEMO_STUDENTS:
        csv_content.write(
            '{email},{first_name},{last_name},{primary_section},student,true,false,{password},{phone},{notes}\n'.format(
                password=DEMO_STUDENT_PASSWORD,
                **student,
            )
        )
    csv_content.seek(0)
    import_students_from_csv(csv_content)

    return {
        user.email: user
        for user in User.objects.filter(email__in=demo_emails).select_related('primary_section')
    }


def _seed_monthly_access_statuses(students):
    today = timezone.localdate()
    current_month = today.replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)

    for month in (current_month, next_month):
        for email, student in students.items():
            access, _created = MonthlyAccessStatus.objects.update_or_create(
                student=student,
                month=month,
                defaults={'notes': 'Demo data seeded by seed_demo_eunoia.'},
            )
            if email in ACTIVE_DEMO_STUDENT_EMAILS:
                activate_student_monthly_access(student=student, month=month)
            elif email in PENDING_DEMO_STUDENT_EMAILS:
                access.mark_pending_payment()
            else:
                suspend_student_monthly_access(student=student, month=month)


def _seed_demo_bookings_and_recoveries(students, admin_user):
    now = timezone.now()
    sessions_by_code = defaultdict(list)
    for session in (
        ClassSession.objects.select_related('section')
        .filter(date__gte=timezone.localdate(), status=SessionStatus.SCHEDULED)
        .order_by('date', 'start_time', 'section__name')
    ):
        sessions_by_code[session.section.code].append(session)

    for section_code in ('reformer_arriba', 'reformer_abajo', 'cadillac'):
        if len(sessions_by_code[section_code]) < 2:
            raise ValueError(f'Not enough future sessions to seed demo data for {section_code}.')

    bookings_created = 0
    recoveries_created = 0

    create_booking(
        session_id=sessions_by_code['reformer_arriba'][0].pk,
        student=students['ada.demo@example.com'],
    )
    bookings_created += 1

    dora_recovery = RecoveryCredit.objects.grant_manual_credit(
        student=students['dora.demo@example.com'],
        section=Section.objects.get(code='cadillac'),
        granted_by=admin_user,
        reference_date=sessions_by_code['cadillac'][1].date,
        notes='Demo manual recovery already used in a future class.',
    )
    recoveries_created += 1
    create_booking(
        session_id=sessions_by_code['cadillac'][1].pk,
        student=students['dora.demo@example.com'],
        used_recovery_credit_id=dora_recovery.pk,
    )
    bookings_created += 1

    eva_session = next(
        (
            session
            for session in sessions_by_code['reformer_arriba']
            if session.starts_at() > now + timedelta(hours=3)
        ),
        None,
    )
    if eva_session is None:
        raise ValueError('Not enough future lead time to create the demo cancellation recovery.')

    eva_booking = create_booking(
        session_id=eva_session.pk,
        student=students['eva.demo@example.com'],
    ).booking
    bookings_created += 1
    cancel_booking(
        booking_id=eva_booking.pk,
        student=students['eva.demo@example.com'],
        actor=students['eva.demo@example.com'],
        when=now,
    )
    recoveries_created += 1

    return {
        'bookings_created': bookings_created,
        'recoveries_created': recoveries_created,
    }


def get_demo_user_matrix():
    return [
        {
            'email': DEMO_ADMIN_EMAIL,
            'password': DEMO_ADMIN_PASSWORD,
            'role': 'admin',
            'description': 'Superuser para `/admin/` y `/staff/`.',
        },
        {
            'email': DEMO_STAFF_EMAIL,
            'password': DEMO_STAFF_PASSWORD,
            'role': 'staff',
            'description': 'Staff operativo para `/staff/` sin superuser.',
        },
        {
            'email': 'ada.demo@example.com',
            'password': DEMO_STUDENT_PASSWORD,
            'role': 'student',
            'description': 'Activa con reserva futura.',
        },
        {
            'email': 'bea.demo@example.com',
            'password': DEMO_STUDENT_PASSWORD,
            'role': 'student',
            'description': 'Impaga con bloqueo operativo.',
        },
        {
            'email': 'clara.demo@example.com',
            'password': DEMO_STUDENT_PASSWORD,
            'role': 'student',
            'description': 'Suspendida.',
        },
        {
            'email': 'dora.demo@example.com',
            'password': DEMO_STUDENT_PASSWORD,
            'role': 'student',
            'description': 'Recuperacion ya usada en una reserva futura.',
        },
        {
            'email': 'eva.demo@example.com',
            'password': DEMO_STUDENT_PASSWORD,
            'role': 'student',
            'description': 'Recuperacion disponible generada por cancelacion.',
        },
        {
            'email': 'sofia.demo@example.com',
            'password': DEMO_STUDENT_PASSWORD,
            'role': 'student',
            'description': 'Usuario limpio para el smoke test automatizado.',
        },
    ]


def run_demo_smoke_flow(*, client, reverse_func):
    with transaction.atomic():
        student = User.objects.get(email='sofia.demo@example.com')
        staff = User.objects.get(email=DEMO_STAFF_EMAIL)

        student_login = client.post(
            reverse_func('login'),
            {'email': student.email, 'password': DEMO_STUDENT_PASSWORD},
        )
        if student_login.status_code != 302:
            raise AssertionError('Demo student login failed.')

        _assert_response_ok(client.get(reverse_func('dashboard')), 'student dashboard')
        _assert_response_ok(client.get(reverse_func('agenda')), 'student agenda')
        _assert_response_ok(client.get(reverse_func('my-bookings')), 'student bookings')

        first_session, second_session = _find_smoke_sessions(student)
        reserve_response = client.post(
            reverse_func('create-booking', args=[first_session.pk]),
            {'next': reverse_func('agenda')},
        )
        if reserve_response.status_code != 302:
            raise AssertionError('Demo booking creation failed.')

        booking = Booking.objects.get(session=first_session, student=student, status='booked')
        cancel_response = client.post(
            reverse_func('cancel-booking', args=[booking.pk]),
            {'next': reverse_func('my-bookings')},
        )
        if cancel_response.status_code != 302:
            raise AssertionError('Demo booking cancellation failed.')

        recovery = RecoveryCredit.objects.filter(
            student=student,
            origin_session=first_session,
        ).latest('pk')
        _assert_response_ok(client.get(reverse_func('use-recovery', args=[recovery.pk])), 'recovery detail')

        recovery_booking_response = client.post(
            reverse_func('create-booking', args=[second_session.pk]),
            {
                'used_recovery_credit_id': recovery.pk,
                'next': reverse_func('my-bookings'),
            },
        )
        if recovery_booking_response.status_code != 302:
            raise AssertionError('Demo recovery booking failed.')

        client.get(reverse_func('logout'))

        staff_login = client.post(
            reverse_func('login'),
            {'email': staff.email, 'password': DEMO_STAFF_PASSWORD},
        )
        if staff_login.status_code != 302:
            raise AssertionError('Demo staff login failed.')

        _assert_response_ok(client.get(reverse_func('admin-student-list')), 'staff student list')
        _assert_response_ok(client.get(reverse_func('admin-class-agenda')), 'staff class agenda')
        _assert_response_ok(
            client.get(reverse_func('admin-student-detail', args=[student.pk])),
            'staff student detail',
        )

        transaction.set_rollback(True)


def _find_smoke_sessions(student):
    future_sessions = list(
        ClassSession.objects.filter(
            section=student.primary_section,
            date__gte=timezone.localdate(),
            status=SessionStatus.SCHEDULED,
        ).order_by('date', 'start_time')
    )
    eligible = [session for session in future_sessions if session.starts_at() > timezone.now() + timedelta(hours=3)]
    if len(eligible) < 2:
        raise AssertionError('Not enough future sessions for the smoke student.')
    return eligible[0], eligible[1]


def _assert_response_ok(response, label):
    if response.status_code != 200:
        raise AssertionError(f'Unexpected status for {label}: {response.status_code}')
