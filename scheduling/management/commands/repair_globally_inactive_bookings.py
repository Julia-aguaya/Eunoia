import csv
from datetime import datetime
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scheduling.models import (
    Booking,
    BookingStatus,
    ClassSession,
    StudentMonthlyPlan,
    StudentMonthlyPlanSlot,
    User,
    normalize_month_start,
)
from scheduling.use_cases import cleanup_global_deactivation


CSV_COLUMNS = (
    'record_type',
    'student_id',
    'student_name',
    'session_id',
    'date',
    'time',
    'section',
    'current_status',
    'plan_id',
    'plan_month',
    'plan_section',
    'plan_slot_ids',
    'plan_slot_details',
    'action',
)


class Command(BaseCommand):
    help = 'Report or clean future bookings and active plan assignments for globally inactive students without deleting plan history.'

    def add_arguments(self, parser):
        parser.add_argument('--from-date', required=True, type=self.parse_date)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--dry-run', action='store_true', default=True)
        mode.add_argument('--apply', action='store_false', dest='dry_run')

    def handle(self, *args, **options):
        from_date = options['from_date']
        apply = not options['dry_run']
        target_month = normalize_month_start(from_date)
        booking_candidates = list(
            Booking.objects.filter(
                status=BookingStatus.BOOKED,
                student__is_active=False,
                session__date__gte=from_date,
            )
            .select_related('student', 'session__section')
            .order_by('session__date', 'session__start_time', 'session__section__name', 'student__last_name', 'student__first_name', 'pk')
        )
        plan_candidates = list(
            StudentMonthlyPlan.objects.filter(
                student__is_active=False,
                month__gte=target_month,
                is_active=True,
            )
            .select_related('student', 'section')
            .prefetch_related('plan_slots__weekly_class_slot')
            .order_by('student__last_name', 'student__first_name', 'student_id', 'section__name', 'pk')
        )

        writer = csv.DictWriter(self.stdout, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        applied_count = 0
        skipped_count = 0
        repaired_student_ids = set()
        for candidate in booking_candidates:
            row = self._row(candidate, action='WOULD_CANCEL')
            if apply:
                with transaction.atomic():
                    try:
                        student = User.objects.select_for_update().get(pk=candidate.student_id)
                    except User.DoesNotExist:
                        row['action'] = 'SKIPPED_DELETED_STUDENT'
                        row['current_status'] = ''
                        skipped_count += 1
                        writer.writerow(row)
                        continue
                    cancelled_booking_ids, _ = cleanup_global_deactivation(
                        student=student,
                        booking_from_date=from_date,
                        plan_reset_from=target_month,
                        only_not_started=False,
                        booking_ids=[candidate.pk],
                        plan_ids=[],
                    )
                    repaired_student_ids.add(student.pk)
                    if candidate.pk not in cancelled_booking_ids:
                        current_status = Booking.objects.filter(pk=candidate.pk).values_list('status', flat=True).first()
                        row['action'] = 'SKIPPED_DELETED_BOOKING' if current_status is None else 'SKIPPED_REVALIDATION'
                        row['current_status'] = current_status or ''
                        skipped_count += 1
                    else:
                        row['action'] = 'CANCELLED'
                        applied_count += 1
            writer.writerow(row)

        for candidate in plan_candidates:
            row = self._plan_row(candidate, action='WOULD_MASK_PLAN')
            if apply:
                with transaction.atomic():
                    # Lock parent before children so plan writers share one order.
                    try:
                        student = User.objects.select_for_update().get(pk=candidate.student_id)
                    except User.DoesNotExist:
                        row['action'] = 'SKIPPED_DELETED_STUDENT'
                        skipped_count += 1
                        writer.writerow(row)
                        continue
                    _, deleted_plan_ids = cleanup_global_deactivation(
                        student=student,
                        booking_from_date=from_date,
                        plan_reset_from=target_month,
                        only_not_started=False,
                        booking_ids=[],
                        plan_ids=[candidate.pk],
                    )
                    repaired_student_ids.add(student.pk)
                    if candidate.pk not in deleted_plan_ids:
                        row['action'] = (
                            'SKIPPED_DELETED_PLAN'
                            if not StudentMonthlyPlan.objects.filter(pk=candidate.pk).exists()
                            else 'SKIPPED_REVALIDATION'
                        )
                        skipped_count += 1
                    else:
                        row['action'] = 'MASKED_PLAN'
                        applied_count += 1
            writer.writerow(row)

        if apply:
            inactive_student_ids = User.objects.filter(is_active=False).exclude(
                pk__in=repaired_student_ids,
            ).order_by('pk').values_list('pk', flat=True)
            for student_id in inactive_student_ids:
                with transaction.atomic():
                    try:
                        student = User.objects.select_for_update().get(pk=student_id)
                    except User.DoesNotExist:
                        continue
                    if not student.is_active:
                        cleanup_global_deactivation(
                            student=student,
                            booking_from_date=from_date,
                            plan_reset_from=target_month,
                            only_not_started=False,
                            booking_ids=[],
                            plan_ids=[],
                        )

        mode = 'apply' if apply else 'dry-run'
        self.stderr.write(
            'repair_globally_inactive_bookings '
            f'mode={mode} booking_candidates={len(booking_candidates)} plan_candidates={len(plan_candidates)} '
            f'applied={applied_count} skipped={skipped_count}'
        )

    @staticmethod
    def _row(booking, *, action):
        return {
            'record_type': 'BOOKING',
            'student_id': booking.student_id,
            'student_name': booking.student.get_full_name(),
            'session_id': booking.session_id,
            'date': booking.session.date.isoformat(),
            'time': booking.session.start_time.strftime('%H:%M'),
            'section': booking.session.section.name,
            'current_status': booking.status,
            'plan_id': '',
            'plan_month': '',
            'plan_section': '',
            'plan_slot_ids': '',
            'plan_slot_details': '',
            'action': action,
        }

    @staticmethod
    def _plan_row(plan, *, action):
        plan_slots = list(plan.plan_slots.all())
        return {
            'record_type': 'MONTHLY_PLAN',
            'student_id': plan.student_id,
            'student_name': plan.student.get_full_name(),
            'session_id': '',
            'date': '',
            'time': '',
            'section': '',
            'current_status': '',
            'plan_id': plan.pk,
            'plan_month': plan.month.isoformat(),
            'plan_section': plan.section.name,
            'plan_slot_ids': '|'.join(str(plan_slot.pk) for plan_slot in plan_slots),
            'plan_slot_details': '|'.join(
                f'{plan_slot.pk}:weekly_slot={plan_slot.weekly_class_slot_id};'
                f'weekday={plan_slot.weekly_class_slot.weekday};'
                f'time={plan_slot.weekly_class_slot.start_time:%H:%M}-{plan_slot.weekly_class_slot.end_time:%H:%M}'
                for plan_slot in plan_slots
            ),
            'action': action,
        }

    @staticmethod
    def parse_date(value):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.')
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.') from exc
