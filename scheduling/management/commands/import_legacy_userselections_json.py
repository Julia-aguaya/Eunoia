from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scheduling.legacy_userselections_import import (
    build_confirmed_section_candidates_by_weekday_and_time,
    LegacyUserSelectionsImportValidationError,
    import_legacy_userselections_from_json,
)
from scheduling.models import Section


class Command(BaseCommand):
    help = 'Import legacy Mongo user selections into StudentMonthlyPlan and StudentMonthlyPlanSlot.'

    def add_arguments(self, parser):
        parser.add_argument('json_path', help='Path to the legacy user selections JSON export.')
        parser.add_argument(
            '--cutoff-month',
            help='Month to import as the legacy snapshot cutoff (YYYY-MM or YYYY-MM-DD). Defaults to the latest lastChange month in the file.',
        )
        parser.add_argument(
            '--default-section',
            help='Fallback section code when students do not have primary_section set.',
        )
        parser.add_argument(
            '--use-confirmed-section-map',
            action='store_true',
            help='Resolve sections from the confirmed manual day/hour mapping instead of relying on primary_section.',
        )
        parser.add_argument(
            '--create-missing-slots',
            action='store_true',
            help='Create missing WeeklyClassSlot rows as 1-hour active slots inside the resolved section.',
        )
        parser.add_argument(
            '--skip-unresolved-sections',
            action='store_true',
            help='Skip plan specs whose section remains ambiguous or conflicting after mapping, instead of aborting the whole import.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and simulate the import without persisting changes.',
        )

    def handle(self, *args, **options):
        json_path = Path(options['json_path'])
        if not json_path.exists() or not json_path.is_file():
            raise CommandError(f'JSON file not found: {json_path}')

        cutoff_month = self._parse_month(options.get('cutoff_month'))
        default_section = None
        default_section_code = options.get('default_section')
        if default_section_code:
            default_section = Section.objects.filter(code=default_section_code).first()
            if default_section is None:
                raise CommandError(f'Unknown section code: {default_section_code}')

        section_candidates_by_slot = None
        if options['use_confirmed_section_map']:
            section_candidates_by_slot = build_confirmed_section_candidates_by_weekday_and_time()

        try:
            result = import_legacy_userselections_from_json(
                json_path=json_path,
                cutoff_month=cutoff_month,
                default_section=default_section,
                section_candidates_by_slot=section_candidates_by_slot,
                create_missing_slots=options['create_missing_slots'],
                skip_unresolved_sections=options['skip_unresolved_sections'],
                dry_run=options['dry_run'],
            )
        except LegacyUserSelectionsImportValidationError as exc:
            raise CommandError(str(exc)) from exc

        mode_label = 'Dry run completed' if options['dry_run'] else 'Import completed'
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode_label}: cutoff {result.cutoff_month:%Y-%m}; '
                f'{result.processed_count} students processed; '
                f'{result.plan_specs_count} plan specs resolved; '
                f'{result.created_plan_count} plans created, {result.updated_plan_count} updated, '
                f'{result.unchanged_plan_count} unchanged; '
                f'{result.created_slot_count} weekly slots created; '
                f'{result.resolved_by_slot_intersection_count} plans resolved by slot intersection, '
                f'{result.resolved_by_primary_section_count} by primary section, '
                f'{result.resolved_by_inferred_section_count} by inferred section; '
                f'{result.unresolved_section_count} unresolved section specs '
                f'({result.ambiguous_section_count} ambiguous, {result.conflicting_section_count} conflicting, '
                f'{result.missing_section_mapping_count} missing mapping); '
                f'{result.skipped_missing_user_count} non-student records skipped; '
                f'{result.skipped_empty_count} empty records skipped.'
            )
        )

    def _parse_month(self, raw_value):
        if not raw_value:
            return None

        for input_format in ('%Y-%m', '%Y-%m-%d'):
            try:
                parsed = datetime.strptime(raw_value, input_format).date()
                return parsed.replace(day=1)
            except ValueError:
                continue

        raise CommandError('--cutoff-month must use YYYY-MM or YYYY-MM-DD.')
