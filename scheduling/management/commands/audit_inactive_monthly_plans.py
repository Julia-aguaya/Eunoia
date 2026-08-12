import csv
from datetime import datetime
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scheduling.models import (
    Booking,
    BookingStatus,
    MonthlyAccessStatus,
    MonthlyAccessStatusType,
    StudentMonthlyPlan,
    User,
    normalize_month_start,
)
from scheduling.use_cases import cleanup_global_deactivation


class Command(BaseCommand):
    help = 'Audit inactive monthly access with inherited fixed plans; apply masks plans and cancels future bookings without deleting history.'

    def add_arguments(self, parser):
        parser.add_argument('--from-date', required=True, type=self.parse_date)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--dry-run', action='store_true', default=True)
        mode.add_argument('--apply', action='store_false', dest='dry_run')

    def handle(self, *args, **options):
        from_date = options['from_date']
        target_month = normalize_month_start(from_date)
        apply = not options['dry_run']
        accesses = list(
            MonthlyAccessStatus.objects.filter(
                month=target_month,
                status__in=[MonthlyAccessStatusType.PENDING_PAYMENT, MonthlyAccessStatusType.SUSPENDED],
            )
            .select_related('student')
            .order_by('student_id')
        )
        writer = csv.DictWriter(self.stdout, fieldnames=(
            'student_id', 'student_name', 'access_status', 'plan_id', 'plan_month',
            'section', 'slot_details', 'future_booking_ids', 'action',
        ))
        writer.writeheader()
        candidates = 0
        applied = 0
        for access in accesses:
            student = access.student
            plans = list(
                StudentMonthlyPlan.objects.filter(student=student, month__lte=target_month, is_active=True)
                .select_related('section')
                .prefetch_related('plan_slots__weekly_class_slot')
                .order_by('section_id', '-month', '-pk')
            )
            effective_by_section = {}
            for plan in plans:
                effective_by_section.setdefault(plan.section_id, plan)
            future_bookings = list(Booking.objects.filter(
                student=student, status=BookingStatus.BOOKED, session__date__gte=from_date,
            ).order_by('pk').values_list('pk', flat=True))
            if not effective_by_section and not future_bookings:
                continue
            candidates += 1
            for plan in effective_by_section.values() or [None]:
                writer.writerow({
                    'student_id': student.pk,
                    'student_name': student.get_full_name(),
                    'access_status': access.status,
                    'plan_id': plan.pk if plan else '',
                    'plan_month': plan.month.isoformat() if plan else '',
                    'section': plan.section.name if plan else '',
                    'slot_details': '|'.join(
                        f'{item.weekly_class_slot.get_weekday_display()} {item.weekly_class_slot.start_time:%H:%M}'
                        for item in plan.plan_slots.all()
                    ) if plan else '',
                    'future_booking_ids': '|'.join(map(str, future_bookings)),
                    'action': 'WOULD_MASK_PLAN_AND_CANCEL_FUTURE_BOOKINGS' if not apply else 'MASKED_PLAN_AND_CANCELLED_FUTURE_BOOKINGS',
                })
            if apply:
                with transaction.atomic():
                    locked_student = User.objects.select_for_update().get(pk=student.pk)
                    cleanup_global_deactivation(
                        student=locked_student,
                        booking_from_date=from_date,
                        plan_reset_from=target_month,
                        only_not_started=False,
                    )
                applied += 1
        self.stderr.write(
            f'audit_inactive_monthly_plans mode={"apply" if apply else "dry-run"} '
            f'candidates={candidates} applied={applied}'
        )

    @staticmethod
    def parse_date(value):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.')
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError(f'Invalid date "{value}". Use YYYY-MM-DD.') from exc
