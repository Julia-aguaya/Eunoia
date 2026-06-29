import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from scheduling.models import Section, StudentMonthlyPlan, User, Weekday, WeeklyClassSlot, normalize_month_start


LEGACY_PLAN_NOTES_START = '[legacy-userselections-import]'
LEGACY_PLAN_NOTES_END = '[/legacy-userselections-import]'
LEGACY_USERSELECTIONS_SOURCE = 'eunoia.userselections.json'
LEGACY_SCHEDULECONFIGS_SOURCE = 'eunoia.scheduleconfigs.json'
LEGACY_USER_ID_PATTERN = re.compile(r'^legacy_user_id=(?P<legacy_id>[^\n]+)$', re.MULTILINE)
PLACEHOLDER_DAY = '__placeholder__'
PLACEHOLDER_HOUR = '__none__'
LEGACY_DAY_TO_WEEKDAY = {
    'lunes': Weekday.MONDAY,
    'martes': Weekday.TUESDAY,
    'miercoles': Weekday.WEDNESDAY,
    'miércoles': Weekday.WEDNESDAY,
    'jueves': Weekday.THURSDAY,
    'viernes': Weekday.FRIDAY,
    'sabado': Weekday.SATURDAY,
    'sábado': Weekday.SATURDAY,
    'domingo': Weekday.SUNDAY,
}
CONFIRMED_SECTION_CANDIDATES_BY_DAY_HOUR = {
    ('martes', '07:00'): ('cadillac', 'reformer_abajo'),
    ('martes', '08:00'): ('cadillac', 'reformer_abajo'),
    ('martes', '09:00'): ('cadillac', 'reformer_abajo'),
    ('martes', '17:00'): ('cadillac', 'reformer_abajo'),
    ('martes', '18:00'): ('cadillac', 'reformer_abajo'),
    ('martes', '19:00'): ('cadillac', 'reformer_abajo'),
    ('jueves', '07:00'): ('cadillac', 'reformer_abajo'),
    ('jueves', '08:00'): ('cadillac', 'reformer_abajo'),
    ('jueves', '09:00'): ('cadillac', 'reformer_abajo'),
    ('jueves', '17:00'): ('cadillac', 'reformer_abajo'),
    ('jueves', '18:00'): ('cadillac', 'reformer_abajo'),
    ('jueves', '19:00'): ('cadillac', 'reformer_abajo'),
    ('lunes', '08:00'): ('reformer_arriba', 'reformer_abajo'),
    ('lunes', '09:00'): ('reformer_arriba', 'reformer_abajo'),
    ('lunes', '10:00'): ('reformer_abajo',),
    ('lunes', '17:00'): ('reformer_arriba', 'reformer_abajo'),
    ('lunes', '18:00'): ('reformer_arriba', 'reformer_abajo'),
    ('lunes', '19:00'): ('reformer_arriba', 'reformer_abajo'),
    ('lunes', '20:00'): ('reformer_abajo',),
    ('miercoles', '08:00'): ('reformer_arriba', 'reformer_abajo'),
    ('miercoles', '09:00'): ('reformer_arriba', 'reformer_abajo'),
    ('miercoles', '17:00'): ('reformer_arriba', 'reformer_abajo'),
    ('miercoles', '18:00'): ('reformer_arriba', 'reformer_abajo'),
    ('miercoles', '19:00'): ('reformer_arriba', 'reformer_abajo'),
    ('miercoles', '20:00'): ('reformer_abajo',),
    ('viernes', '08:00'): ('reformer_abajo',),
    ('viernes', '09:00'): ('reformer_abajo',),
    ('viernes', '17:00'): ('reformer_arriba', 'reformer_abajo'),
    ('viernes', '18:00'): ('reformer_arriba', 'reformer_abajo'),
    ('viernes', '19:00'): ('reformer_abajo',),
    ('jueves', '10:00'): ('reformer_abajo',),
    ('jueves', '20:00'): ('reformer_abajo',),
    ('martes', '10:00'): ('reformer_abajo',),
    ('martes', '20:00'): ('reformer_abajo',),
}


class LegacyUserSelectionsImportValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('\n'.join(errors))


@dataclass(frozen=True)
class ParsedLegacySelectionSlot:
    weekday: int
    start_time: time


@dataclass(frozen=True)
class ParsedLegacyUserSelection:
    source_index: int
    legacy_selection_id: str
    legacy_user_id: str
    original_slots: tuple[ParsedLegacySelectionSlot, ...]
    temporary_slots: tuple[ParsedLegacySelectionSlot, ...]
    has_real_temporary_slots: bool
    changes_this_month: int
    last_change_at: datetime | None


@dataclass(frozen=True)
class PlannedMonthlySelection:
    month: date
    selection_kind: str
    slots: tuple[ParsedLegacySelectionSlot, ...]


@dataclass(frozen=True)
class LegacyUserSelectionImportResult:
    processed_count: int
    plan_specs_count: int
    created_plan_count: int
    updated_plan_count: int
    unchanged_plan_count: int
    created_slot_count: int
    skipped_missing_user_count: int
    unresolved_section_count: int
    resolved_by_slot_intersection_count: int
    resolved_by_primary_section_count: int
    resolved_by_inferred_section_count: int
    ambiguous_section_count: int
    conflicting_section_count: int
    missing_section_mapping_count: int
    missing_slot_count: int
    skipped_empty_count: int
    cutoff_month: date


@dataclass(frozen=True)
class SectionResolution:
    section: Section | None
    status: str
    details: tuple[str, ...] = ()


def build_confirmed_section_candidates_by_weekday_and_time():
    candidates_by_slot = {}
    for (raw_day, raw_hour), section_codes in CONFIRMED_SECTION_CANDIDATES_BY_DAY_HOUR.items():
        weekday = LEGACY_DAY_TO_WEEKDAY[_normalize_legacy_day(raw_day)]
        candidates_by_slot[(weekday, time.fromisoformat(raw_hour))] = tuple(section_codes)
    return candidates_by_slot


def import_legacy_userselections_from_json(
    *,
    json_path,
    cutoff_month=None,
    default_section=None,
    section_candidates_by_slot=None,
    create_missing_slots=False,
    skip_unresolved_sections=False,
    dry_run=False,
):
    records = load_legacy_userselections(json_path)
    effective_cutoff_month = cutoff_month or infer_cutoff_month(records)
    next_month = _shift_month(effective_cutoff_month, 1)

    users_by_legacy_id = {
        legacy_id: user
        for user in User.objects.filter(role='student')
        for legacy_id in [_extract_user_legacy_id(user.notes)]
        if legacy_id
    }

    sections_by_code = {section.code: section for section in Section.objects.all()}
    existing_slots_by_key = {
        (slot.section_id, slot.weekday, slot.start_time): slot
        for slot in WeeklyClassSlot.objects.select_related('section')
    }

    processed_count = 0
    plan_specs_count = 0
    created_plan_count = 0
    updated_plan_count = 0
    unchanged_plan_count = 0
    created_slot_count = 0
    skipped_missing_user_count = 0
    unresolved_section_count = 0
    resolved_by_slot_intersection_count = 0
    resolved_by_primary_section_count = 0
    resolved_by_inferred_section_count = 0
    ambiguous_section_count = 0
    conflicting_section_count = 0
    missing_section_mapping_count = 0
    missing_slot_count = 0
    skipped_empty_count = 0
    errors = []

    with transaction.atomic():
        for record in records:
            user = users_by_legacy_id.get(record.legacy_user_id)
            if user is None:
                skipped_missing_user_count += 1
                continue

            planned_monthly_selections = build_planned_monthly_selections(
                record,
                cutoff_month=effective_cutoff_month,
                next_month=next_month,
            )
            if not planned_monthly_selections:
                skipped_empty_count += 1
                continue

            processed_count += 1
            inferred_section = _infer_record_section_from_planned_selections(
                planned_monthly_selections=planned_monthly_selections,
                section_candidates_by_slot=section_candidates_by_slot,
                sections_by_code=sections_by_code,
            )

            for planned_selection in planned_monthly_selections:
                plan_specs_count += 1
                resolution = _resolve_section_for_planned_selection(
                    user=user,
                    planned_selection=planned_selection,
                    default_section=default_section,
                    inferred_section=inferred_section,
                    section_candidates_by_slot=section_candidates_by_slot,
                    sections_by_code=sections_by_code,
                )
                if resolution.section is None:
                    unresolved_section_count += 1
                    if resolution.status == 'ambiguous':
                        ambiguous_section_count += 1
                    elif resolution.status == 'conflicting':
                        conflicting_section_count += 1
                    elif resolution.status == 'missing_mapping':
                        missing_section_mapping_count += 1

                    error_message = _format_unresolved_section_error(
                        source_index=record.source_index,
                        email=user.email,
                        planned_selection=planned_selection,
                        resolution=resolution,
                    )
                    if skip_unresolved_sections:
                        continue
                    errors.append(error_message)
                    continue

                if resolution.status == 'slot_intersection':
                    resolved_by_slot_intersection_count += 1
                elif resolution.status == 'primary_section':
                    resolved_by_primary_section_count += 1
                elif resolution.status == 'inferred_section':
                    resolved_by_inferred_section_count += 1

                section = resolution.section
                slot_objects = []
                missing_for_plan = []

                for parsed_slot in planned_selection.slots:
                    slot_key = (section.id, parsed_slot.weekday, parsed_slot.start_time)
                    weekly_slot = existing_slots_by_key.get(slot_key)
                    if weekly_slot is not None and not weekly_slot.is_active and create_missing_slots:
                        weekly_slot.is_active = True
                        weekly_slot.end_time = _derive_end_time(parsed_slot.start_time)
                        weekly_slot.notes = _build_created_slot_note()
                        weekly_slot.save(update_fields=['is_active', 'end_time', 'notes', 'updated_at'])
                    if weekly_slot is None and create_missing_slots:
                        weekly_slot = WeeklyClassSlot.objects.create(
                            section=section,
                            weekday=parsed_slot.weekday,
                            start_time=parsed_slot.start_time,
                            end_time=_derive_end_time(parsed_slot.start_time),
                            is_active=True,
                            notes=_build_created_slot_note(),
                        )
                        existing_slots_by_key[slot_key] = weekly_slot
                        created_slot_count += 1

                    if weekly_slot is None:
                        missing_for_plan.append(parsed_slot)
                        continue
                    if not weekly_slot.is_active:
                        missing_for_plan.append(parsed_slot)
                        continue

                    slot_objects.append(weekly_slot)

                if missing_for_plan:
                    missing_slot_count += len(missing_for_plan)
                    errors.append(
                        _format_missing_slot_error(
                            source_index=record.source_index,
                            email=user.email,
                            section_code=section.code,
                            planned_selection=planned_selection,
                            missing_slots=missing_for_plan,
                        )
                    )
                    continue

                changed, created = _upsert_monthly_plan(
                    student=user,
                    section=section,
                    planned_selection=planned_selection,
                    slot_objects=slot_objects,
                    legacy_selection_id=record.legacy_selection_id,
                )
                if created:
                    created_plan_count += 1
                elif changed:
                    updated_plan_count += 1
                else:
                    unchanged_plan_count += 1

        if errors:
            raise LegacyUserSelectionsImportValidationError(errors)

        if dry_run:
            transaction.set_rollback(True)

    return LegacyUserSelectionImportResult(
        processed_count=processed_count,
        plan_specs_count=plan_specs_count,
        created_plan_count=created_plan_count,
        updated_plan_count=updated_plan_count,
        unchanged_plan_count=unchanged_plan_count,
        created_slot_count=created_slot_count,
        skipped_missing_user_count=skipped_missing_user_count,
        unresolved_section_count=unresolved_section_count,
        resolved_by_slot_intersection_count=resolved_by_slot_intersection_count,
        resolved_by_primary_section_count=resolved_by_primary_section_count,
        resolved_by_inferred_section_count=resolved_by_inferred_section_count,
        ambiguous_section_count=ambiguous_section_count,
        conflicting_section_count=conflicting_section_count,
        missing_section_mapping_count=missing_section_mapping_count,
        missing_slot_count=missing_slot_count,
        skipped_empty_count=skipped_empty_count,
        cutoff_month=effective_cutoff_month,
    )


def _infer_record_section_from_planned_selections(*, planned_monthly_selections, section_candidates_by_slot, sections_by_code):
    if not section_candidates_by_slot:
        return None

    resolved_codes = set()
    for planned_selection in planned_monthly_selections:
        candidate_sets = []
        for parsed_slot in planned_selection.slots:
            candidate_codes = section_candidates_by_slot.get((parsed_slot.weekday, parsed_slot.start_time))
            if not candidate_codes:
                candidate_sets = []
                break
            candidate_sets.append(set(candidate_codes))

        common_candidate_codes = set.intersection(*candidate_sets) if candidate_sets else set()
        if len(common_candidate_codes) == 1:
            resolved_codes.update(common_candidate_codes)

    if len(resolved_codes) != 1:
        return None

    return sections_by_code.get(next(iter(resolved_codes)))


def load_legacy_userselections(json_path):
    path = Path(json_path)
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise LegacyUserSelectionsImportValidationError([f'JSON file not found: {path}']) from exc
    except OSError as exc:
        raise LegacyUserSelectionsImportValidationError([f'Could not read JSON file: {exc}']) from exc
    except json.JSONDecodeError as exc:
        raise LegacyUserSelectionsImportValidationError([f'Invalid JSON file: {exc}']) from exc

    if not isinstance(payload, list):
        raise LegacyUserSelectionsImportValidationError(
            ['The JSON file must contain a top-level array of user selections.']
        )

    records = []
    errors = []

    for index, raw_record in enumerate(payload, start=1):
        if not isinstance(raw_record, dict):
            errors.append(f'Entry {index}: expected an object.')
            continue

        legacy_selection_id = _extract_legacy_id(raw_record.get('_id'))
        legacy_user_id = _extract_legacy_id(raw_record.get('user'))
        changes_this_month = raw_record.get('changesThisMonth')

        entry_errors = []
        if not legacy_selection_id:
            entry_errors.append(f'Entry {index}: missing _id.$oid.')
        if not legacy_user_id:
            entry_errors.append(f'Entry {index}: missing user.$oid.')
        if not isinstance(changes_this_month, int):
            entry_errors.append(f'Entry {index}: changesThisMonth must be an integer.')

        try:
            original_slots = _parse_selection_collection(raw_record.get('originalSelections'), index=index, field_name='originalSelections')
        except ValueError as exc:
            entry_errors.append(str(exc))
            original_slots = ()

        try:
            temporary_slots, has_real_temporary_slots = _parse_temporary_selection_collection(
                raw_record.get('temporarySelections'),
                index=index,
            )
        except ValueError as exc:
            entry_errors.append(str(exc))
            temporary_slots = ()
            has_real_temporary_slots = False

        try:
            last_change_at = _parse_legacy_datetime(raw_record.get('lastChange'))
        except ValueError as exc:
            entry_errors.append(f'Entry {index}: invalid lastChange. {exc}')
            last_change_at = None

        if entry_errors:
            errors.extend(entry_errors)
            continue

        records.append(
            ParsedLegacyUserSelection(
                source_index=index,
                legacy_selection_id=legacy_selection_id,
                legacy_user_id=legacy_user_id,
                original_slots=original_slots,
                temporary_slots=temporary_slots,
                has_real_temporary_slots=has_real_temporary_slots,
                changes_this_month=changes_this_month,
                last_change_at=last_change_at,
            )
        )

    if errors:
        raise LegacyUserSelectionsImportValidationError(errors)

    return records


def infer_cutoff_month(records):
    last_change_dates = [record.last_change_at.date() for record in records if record.last_change_at is not None]
    if last_change_dates:
        return normalize_month_start(max(last_change_dates))
    return normalize_month_start(timezone.localdate())


def build_planned_monthly_selections(record, *, cutoff_month, next_month):
    if record.has_real_temporary_slots:
        planned = []
        if record.temporary_slots:
            planned.append(
                PlannedMonthlySelection(
                    month=cutoff_month,
                    selection_kind='temporary',
                    slots=record.temporary_slots,
                )
            )
        if record.original_slots and record.original_slots != record.temporary_slots:
            planned.append(
                PlannedMonthlySelection(
                    month=next_month,
                    selection_kind='original',
                    slots=record.original_slots,
                )
            )
        return tuple(planned)

    if record.original_slots:
        return (
            PlannedMonthlySelection(
                month=cutoff_month,
                selection_kind='original',
                slots=record.original_slots,
            ),
        )

    return ()


def _upsert_monthly_plan(
    *,
    student,
    section,
    planned_selection,
    slot_objects,
    legacy_selection_id,
    note_metadata=None,
):
    plan, created = StudentMonthlyPlan.objects.get_or_create(
        student=student,
        month=planned_selection.month,
        section=section,
        defaults={
            'notes': _build_plan_note(
                existing_notes='',
                planned_selection=planned_selection,
                legacy_selection_id=legacy_selection_id,
                metadata_lines=note_metadata,
            ),
        },
    )

    changed = created
    update_fields = []

    managed_note = _build_plan_note(
        existing_notes=plan.notes,
        planned_selection=planned_selection,
        legacy_selection_id=legacy_selection_id,
        metadata_lines=note_metadata,
    )
    if plan.section_id != section.id:
        plan.section = section
        update_fields.append('section')
    if plan.notes != managed_note:
        plan.notes = managed_note
        update_fields.append('notes')
    if update_fields:
        plan.save(update_fields=update_fields + ['updated_at'])
        changed = True

    current_slot_ids = list(plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position'))
    ordered_target_slot_ids = [slot.pk for slot in slot_objects]

    if current_slot_ids != ordered_target_slot_ids:
        plan.assign_weekly_slots(slot_objects)
        changed = True

    return changed, created


def _parse_selection_collection(raw_value, *, index, field_name):
    if raw_value in (None, ''):
        return ()
    if not isinstance(raw_value, list):
        raise ValueError(f'Entry {index}: {field_name} must be an array.')

    seen = set()
    parsed = []
    for position, raw_slot in enumerate(raw_value, start=1):
        if isinstance(raw_slot, dict):
            raw_day = str(raw_slot.get('day') or '').strip()
            raw_hour = str(raw_slot.get('hour') or '').strip()
            if not raw_day and not raw_hour:
                continue
        parsed_slot = _parse_selection_slot(raw_slot, index=index, field_name=field_name, position=position)
        key = (parsed_slot.weekday, parsed_slot.start_time)
        if key in seen:
            raise ValueError(
                f'Entry {index}: {field_name} contains a duplicated slot for {_format_slot_label(parsed_slot)}.'
            )
        seen.add(key)
        parsed.append(parsed_slot)
    return tuple(parsed)


def _parse_temporary_selection_collection(raw_value, *, index):
    if raw_value in (None, ''):
        return (), False
    if not isinstance(raw_value, list):
        raise ValueError(f'Entry {index}: temporarySelections must be an array.')

    parsed = []
    has_real_temporary_slots = False
    seen = set()
    for position, raw_slot in enumerate(raw_value, start=1):
        if not isinstance(raw_slot, dict):
            raise ValueError(f'Entry {index}: temporarySelections[{position}] must be an object.')

        raw_day = str(raw_slot.get('day') or '').strip()
        raw_hour = str(raw_slot.get('hour') or '').strip()
        if raw_day == PLACEHOLDER_DAY or raw_hour == PLACEHOLDER_HOUR:
            continue

        parsed_slot = _parse_selection_slot(raw_slot, index=index, field_name='temporarySelections', position=position)
        key = (parsed_slot.weekday, parsed_slot.start_time)
        if key in seen:
            raise ValueError(
                f'Entry {index}: temporarySelections contains a duplicated slot for {_format_slot_label(parsed_slot)}.'
            )
        seen.add(key)
        parsed.append(parsed_slot)
        has_real_temporary_slots = True

    return tuple(parsed), has_real_temporary_slots


def _parse_selection_slot(raw_slot, *, index, field_name, position):
    if not isinstance(raw_slot, dict):
        raise ValueError(f'Entry {index}: {field_name}[{position}] must be an object.')

    raw_day = str(raw_slot.get('day') or '').strip()
    raw_hour = str(raw_slot.get('hour') or '').strip()
    if not raw_day:
        raise ValueError(f'Entry {index}: {field_name}[{position}] day is required.')
    if not raw_hour:
        raise ValueError(f'Entry {index}: {field_name}[{position}] hour is required.')

    weekday = LEGACY_DAY_TO_WEEKDAY.get(_normalize_legacy_day(raw_day))
    if weekday is None:
        raise ValueError(f'Entry {index}: unsupported day "{raw_day}" in {field_name}[{position}].')

    try:
        start_time = time.fromisoformat(raw_hour)
    except ValueError as exc:
        raise ValueError(f'Entry {index}: invalid hour "{raw_hour}" in {field_name}[{position}].') from exc

    return ParsedLegacySelectionSlot(weekday=weekday, start_time=start_time)


def _build_plan_note(*, existing_notes, planned_selection, legacy_selection_id, metadata_lines=None):
    base_notes = (existing_notes or '').strip()
    start_index = base_notes.find(LEGACY_PLAN_NOTES_START)
    end_index = base_notes.find(LEGACY_PLAN_NOTES_END)
    if start_index != -1 and end_index != -1 and end_index > start_index:
        managed_prefix = base_notes[:start_index].rstrip()
        managed_suffix = base_notes[end_index + len(LEGACY_PLAN_NOTES_END):].strip()
        base_notes = '\n\n'.join(bit for bit in (managed_prefix, managed_suffix) if bit)

    block_lines = [
        LEGACY_PLAN_NOTES_START,
        f'source={LEGACY_USERSELECTIONS_SOURCE}',
        f'legacy_userselection_id={legacy_selection_id}',
        f'selection_kind={planned_selection.selection_kind}',
        f'effective_month={planned_selection.month.isoformat()}',
    ]
    for metadata_line in metadata_lines or ():
        if metadata_line:
            block_lines.append(str(metadata_line))
    block_lines.append(LEGACY_PLAN_NOTES_END)
    managed_block = '\n'.join(block_lines)
    if not base_notes:
        return managed_block
    return f'{base_notes}\n\n{managed_block}'


def _build_created_slot_note():
    return (
        f'{LEGACY_PLAN_NOTES_START}\n'
        f'source={LEGACY_SCHEDULECONFIGS_SOURCE}\n'
        f'created_by=legacy_userselections_import\n'
        f'{LEGACY_PLAN_NOTES_END}'
    )


def _format_missing_slot_error(*, source_index, email, section_code, planned_selection, missing_slots):
    formatted_slots = ', '.join(_format_slot_label(slot) for slot in missing_slots)
    return (
        f'Entry {source_index}: missing active WeeklyClassSlot rows for {email} '
        f'in section {section_code} during {planned_selection.month:%Y-%m} '
        f'({planned_selection.selection_kind}): {formatted_slots}.'
    )


def _format_unresolved_section_error(*, source_index, email, planned_selection, resolution):
    formatted_slots = ', '.join(_format_slot_label(slot) for slot in planned_selection.slots)
    detail_suffix = ''
    if resolution.details:
        detail_suffix = f' Details: {", ".join(resolution.details)}.'
    return (
        f'Entry {source_index}: could not resolve section for {email} '
        f'during {planned_selection.month:%Y-%m} ({planned_selection.selection_kind}) '
        f'with slots [{formatted_slots}] because status={resolution.status}.{detail_suffix}'
    )


def _format_slot_label(parsed_slot):
    weekday_map = {
        Weekday.MONDAY: 'Monday',
        Weekday.TUESDAY: 'Tuesday',
        Weekday.WEDNESDAY: 'Wednesday',
        Weekday.THURSDAY: 'Thursday',
        Weekday.FRIDAY: 'Friday',
        Weekday.SATURDAY: 'Saturday',
        Weekday.SUNDAY: 'Sunday',
    }
    return f'{weekday_map.get(parsed_slot.weekday, parsed_slot.weekday)} {parsed_slot.start_time.strftime("%H:%M")}'


def _extract_user_legacy_id(notes):
    if not notes:
        return ''
    match = LEGACY_USER_ID_PATTERN.search(notes)
    return match.group('legacy_id').strip() if match else ''


def _extract_legacy_id(raw_id):
    if isinstance(raw_id, dict):
        return str(raw_id.get('$oid') or '').strip()
    return ''


def _parse_legacy_datetime(raw_value):
    if raw_value in (None, ''):
        return None
    if not isinstance(raw_value, dict) or '$date' not in raw_value:
        raise ValueError('Expected a Mongo-style {"$date": ...} object.')

    raw_date = str(raw_value['$date']).strip()
    if not raw_date:
        return None

    normalized_value = raw_date.replace('Z', '+00:00')
    parsed = datetime.fromisoformat(normalized_value)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _derive_end_time(start_time_value):
    base_datetime = datetime.combine(date(2000, 1, 1), start_time_value)
    return (base_datetime + timedelta(hours=1)).time()


def _shift_month(month_start, delta):
    return normalize_month_start(
        (datetime.combine(month_start, time.min) + timedelta(days=32 * delta)).date()
    )


def _normalize_legacy_day(raw_day):
    normalized = unicodedata.normalize('NFKD', str(raw_day or '').strip().lower())
    return ''.join(character for character in normalized if not unicodedata.combining(character))


def _resolve_section_for_planned_selection(
    *,
    user,
    planned_selection,
    default_section,
    inferred_section,
    section_candidates_by_slot,
    sections_by_code,
):
    if section_candidates_by_slot:
        candidate_sets = []
        missing_mapping_slots = []
        for parsed_slot in planned_selection.slots:
            candidate_codes = section_candidates_by_slot.get((parsed_slot.weekday, parsed_slot.start_time))
            if not candidate_codes:
                missing_mapping_slots.append(_format_slot_label(parsed_slot))
                continue
            candidate_sets.append(set(candidate_codes))

        if missing_mapping_slots:
            return SectionResolution(
                section=None,
                status='missing_mapping',
                details=tuple(missing_mapping_slots),
            )

        common_candidate_codes = set.intersection(*candidate_sets) if candidate_sets else set()
        if len(common_candidate_codes) == 1:
            section_code = next(iter(common_candidate_codes))
            return SectionResolution(
                section=sections_by_code.get(section_code),
                status='slot_intersection',
                details=(section_code,),
            )
        if len(common_candidate_codes) > 1:
            if user.primary_section_id and user.primary_section.code in common_candidate_codes:
                return SectionResolution(
                    section=user.primary_section,
                    status='primary_section',
                    details=tuple(sorted(common_candidate_codes)),
                )
            if inferred_section is not None and inferred_section.code in common_candidate_codes:
                return SectionResolution(
                    section=inferred_section,
                    status='inferred_section',
                    details=tuple(sorted(common_candidate_codes)),
                )
            return SectionResolution(
                section=None,
                status='ambiguous',
                details=tuple(sorted(common_candidate_codes)),
            )
        return SectionResolution(
            section=None,
            status='conflicting',
            details=tuple(sorted({code for candidate_codes in candidate_sets for code in candidate_codes})),
        )

    section = default_section or user.primary_section
    if section is None:
        return SectionResolution(section=None, status='missing_primary_section')
    return SectionResolution(section=section, status='primary_section', details=(section.code,))
