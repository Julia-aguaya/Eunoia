import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from django.db import transaction

from scheduling.legacy_userselections_import import (
    LegacyUserSelectionsImportValidationError,
    _build_created_slot_note,
    _build_plan_note,
    _derive_end_time,
    _extract_user_legacy_id,
    _infer_record_section_from_planned_selections,
    _resolve_section_for_planned_selection,
    _shift_month,
    _upsert_monthly_plan,
    build_confirmed_section_candidates_by_weekday_and_time,
    build_planned_monthly_selections,
    infer_cutoff_month,
    load_legacy_userselections,
)
from scheduling.models import Section, StudentMonthlyPlan, User, WeeklyClassSlot


RESOLUTION_COLUMN_CANDIDATES = (
    'resolved_section',
    'resolvedsection',
    'manual_section',
    'manualsection',
    'section_resolution',
    'sectionresolution',
    'manual_resolution',
    'manualresolution',
    'section',
)
MANUAL_OVERRIDE_COLUMN_CANDIDATES = (
    'manual_override',
    'allow_manual_override',
    'force_manual_override',
)
MANUAL_OVERRIDE_REASON_COLUMN_CANDIDATES = (
    'manual_override_reason',
    'override_reason',
    'resolution_override_reason',
)
SECTION_CODE_NORMALIZATION = {
    'refomer_abajo': 'reformer_abajo',
}
TRUE_VALUES = {'1', 'true', 'yes', 'y', 'si', 'sí'}


@dataclass(frozen=True)
class CuratedResolutionRow:
    row_number: int
    source_index: int
    student_id: int
    student_email: str
    legacy_user_id: str
    legacy_userselection_id: str
    month: date
    selection_kind: str
    resolved_section_code: str
    possible_section_codes: tuple[str, ...]
    manual_override: bool
    manual_override_reason: str


@dataclass(frozen=True)
class LegacyUserSelectionsManualBackfillResult:
    csv_path: str
    resolution_column: str
    manual_override_column: str | None
    manual_override_reason_column: str | None
    normalized_resolution_count: int
    scanned_case_count: int
    pending_case_count: int
    manual_override_count: int
    created_plan_count: int
    updated_plan_count: int
    unchanged_plan_count: int
    created_slot_count: int
    skipped_existing_plan_count: int


def import_legacy_userselections_manual_backfill_from_csv(
    *,
    csv_path,
    json_path,
    create_missing_slots=False,
    dry_run=False,
):
    (
        rows,
        resolution_column,
        manual_override_column,
        manual_override_reason_column,
        normalized_resolution_count,
    ) = load_curated_resolution_rows(csv_path)
    records = load_legacy_userselections(json_path)
    cutoff_month = infer_cutoff_month(records)
    next_month = _shift_month(cutoff_month, 1)
    records_by_source_index = {record.source_index: record for record in records}
    users_by_id = {
        user.id: user
        for user in User.objects.filter(role='student').select_related('primary_section')
    }
    sections_by_code = {section.code: section for section in Section.objects.all()}
    existing_slots_by_key = {
        (slot.section_id, slot.weekday, slot.start_time): slot
        for slot in WeeklyClassSlot.objects.select_related('section')
    }
    section_candidates_by_slot = build_confirmed_section_candidates_by_weekday_and_time()

    errors = []
    created_plan_count = 0
    updated_plan_count = 0
    unchanged_plan_count = 0
    created_slot_count = 0
    skipped_existing_plan_count = 0
    pending_case_count = 0
    manual_override_count = 0

    with transaction.atomic():
        for row in rows:
            record = records_by_source_index.get(row.source_index)
            if record is None:
                errors.append(f'CSV row {row.row_number}: source_index {row.source_index} was not found in {json_path}.')
                continue

            if record.legacy_selection_id != row.legacy_userselection_id:
                errors.append(
                    f'CSV row {row.row_number}: legacy_userselection_id {row.legacy_userselection_id} '
                    f'does not match source_index {row.source_index} ({record.legacy_selection_id}).'
                )
                continue

            user = users_by_id.get(row.student_id)
            if user is None:
                errors.append(f'CSV row {row.row_number}: student_id {row.student_id} was not found.')
                continue

            user_legacy_id = _extract_user_legacy_id(user.notes)
            if user_legacy_id != row.legacy_user_id:
                errors.append(
                    f'CSV row {row.row_number}: student_id {row.student_id} has legacy_user_id '
                    f'{user_legacy_id or "<missing>"}, expected {row.legacy_user_id}.'
                )
                continue

            planned_monthly_selections = build_planned_monthly_selections(
                record,
                cutoff_month=cutoff_month,
                next_month=next_month,
            )
            inferred_section = _infer_record_section_from_planned_selections(
                planned_monthly_selections=planned_monthly_selections,
                section_candidates_by_slot=section_candidates_by_slot,
                sections_by_code=sections_by_code,
            )
            planned_selection = _match_planned_selection(row=row, planned_monthly_selections=planned_monthly_selections)
            if planned_selection is None:
                errors.append(
                    f'CSV row {row.row_number}: no planned selection found for '
                    f'{row.month.isoformat()} / {row.selection_kind} in source_index {row.source_index}.'
                )
                continue

            resolution = _resolve_section_for_planned_selection(
                user=user,
                planned_selection=planned_selection,
                default_section=None,
                inferred_section=inferred_section,
                section_candidates_by_slot=section_candidates_by_slot,
                sections_by_code=sections_by_code,
            )
            if resolution.section is not None:
                errors.append(
                    f'CSV row {row.row_number}: {row.student_email} / {row.month.isoformat()} / {row.selection_kind} '
                    f'is no longer pending because it resolves automatically as {resolution.section.code} '
                    f'(status={resolution.status}).'
                )
                continue

            pending_case_count += 1
            if row.manual_override:
                manual_override_count += 1
            section = sections_by_code.get(row.resolved_section_code)
            if section is None:
                errors.append(
                    f'CSV row {row.row_number}: resolved section {row.resolved_section_code} does not exist.'
                )
                continue
            plan = StudentMonthlyPlan.objects.filter(student=user, month=row.month).first()
            if plan is not None and not _plan_matches_legacy_identity(
                plan=plan,
                legacy_userselection_id=row.legacy_userselection_id,
                selection_kind=row.selection_kind,
                month=row.month,
            ):
                errors.append(
                    f'CSV row {row.row_number}: student {row.student_email} already has a '
                    f'StudentMonthlyPlan for {row.month.isoformat()} outside this legacy backfill.'
                )
                continue
            if plan is not None:
                skipped_existing_plan_count += 1

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

                if weekly_slot is None or not weekly_slot.is_active:
                    missing_for_plan.append(parsed_slot)
                    continue
                slot_objects.append(weekly_slot)

            if missing_for_plan:
                formatted_slots = ', '.join(
                    f'{slot.weekday} {slot.start_time.strftime("%H:%M")}' for slot in missing_for_plan
                )
                errors.append(
                    f'CSV row {row.row_number}: missing active WeeklyClassSlot rows for '
                    f'{row.student_email} in section {section.code}: {formatted_slots}.'
                )
                continue

            changed, created = _upsert_monthly_plan(
                student=user,
                section=section,
                planned_selection=planned_selection,
                slot_objects=slot_objects,
                legacy_selection_id=row.legacy_userselection_id,
                note_metadata=_build_manual_override_note_metadata(row),
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

    return LegacyUserSelectionsManualBackfillResult(
        csv_path=str(Path(csv_path)),
        resolution_column=resolution_column,
        manual_override_column=manual_override_column,
        manual_override_reason_column=manual_override_reason_column,
        normalized_resolution_count=normalized_resolution_count,
        scanned_case_count=len(rows),
        pending_case_count=pending_case_count,
        manual_override_count=manual_override_count,
        created_plan_count=created_plan_count,
        updated_plan_count=updated_plan_count,
        unchanged_plan_count=unchanged_plan_count,
        created_slot_count=created_slot_count,
        skipped_existing_plan_count=skipped_existing_plan_count,
    )


def load_curated_resolution_rows(csv_path):
    path = Path(csv_path)
    try:
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            resolution_column = _detect_resolution_column(fieldnames)
            manual_override_column = _detect_optional_column(fieldnames, MANUAL_OVERRIDE_COLUMN_CANDIDATES)
            manual_override_reason_column = _detect_optional_column(fieldnames, MANUAL_OVERRIDE_REASON_COLUMN_CANDIDATES)
            rows = list(reader)
    except FileNotFoundError as exc:
        raise LegacyUserSelectionsImportValidationError([f'CSV file not found: {path}']) from exc
    except OSError as exc:
        raise LegacyUserSelectionsImportValidationError([f'Could not read CSV file: {exc}']) from exc

    normalized_resolution_count = 0
    parsed_rows = []
    errors = []
    seen_row_keys = set()

    for index, raw_row in enumerate(rows, start=2):
        try:
            student_id = int(str(raw_row.get('student_id') or '').strip())
        except ValueError:
            errors.append(f'CSV row {index}: student_id must be an integer.')
            continue

        try:
            source_index = int(str(raw_row.get('source_index') or '').strip())
        except ValueError:
            errors.append(f'CSV row {index}: source_index must be an integer.')
            continue

        raw_resolution = str(raw_row.get(resolution_column) or '').strip()
        if not raw_resolution:
            errors.append(f'CSV row {index}: {resolution_column} is required.')
            continue

        normalized_resolution = _normalize_section_code(raw_resolution)
        if normalized_resolution != raw_resolution:
            normalized_resolution_count += 1

        possible_sections = tuple(
            _normalize_section_code(section)
            for section in str(raw_row.get('possible_sections') or '').split('|')
            if str(section).strip()
        )
        if not possible_sections:
            errors.append(f'CSV row {index}: possible_sections is required.')
            continue
        manual_override = _parse_manual_override(raw_row.get(manual_override_column) if manual_override_column else None)
        manual_override_reason = str(raw_row.get(manual_override_reason_column) or '').strip() if manual_override_reason_column else ''
        if manual_override and not manual_override_reason:
            errors.append(
                f'CSV row {index}: {manual_override_reason_column or "manual_override_reason"} is required when manual override is enabled.'
            )
            continue
        if normalized_resolution not in possible_sections and not manual_override:
            errors.append(
                f'CSV row {index}: resolved section {normalized_resolution} is not among '
                f'possible_sections ({", ".join(possible_sections)}).'
            )
            continue

        selection_kind = str(raw_row.get('selection_kind') or '').strip()
        if selection_kind not in {'original', 'temporary'}:
            errors.append(f'CSV row {index}: invalid selection_kind {selection_kind!r}.')
            continue

        month_value = str(raw_row.get('month') or '').strip()
        try:
            month = datetime.strptime(month_value, '%Y-%m-%d').date()
        except ValueError:
            errors.append(f'CSV row {index}: month must use YYYY-MM-DD.')
            continue

        row_key = (source_index, month.isoformat(), selection_kind)
        if row_key in seen_row_keys:
            errors.append(
                f'CSV row {index}: duplicate source_index/month/selection_kind combination '
                f'{source_index}/{month.isoformat()}/{selection_kind}.'
            )
            continue
        seen_row_keys.add(row_key)

        parsed_rows.append(
            CuratedResolutionRow(
                row_number=index,
                source_index=source_index,
                student_id=student_id,
                student_email=str(raw_row.get('student_email') or '').strip(),
                legacy_user_id=str(raw_row.get('legacy_user_id') or '').strip(),
                legacy_userselection_id=str(raw_row.get('legacy_userselection_id') or '').strip(),
                month=month,
                selection_kind=selection_kind,
                resolved_section_code=normalized_resolution,
                possible_section_codes=possible_sections,
                manual_override=manual_override,
                manual_override_reason=manual_override_reason,
            )
        )

    if errors:
        raise LegacyUserSelectionsImportValidationError(errors)
    return (
        tuple(parsed_rows),
        resolution_column,
        manual_override_column,
        manual_override_reason_column,
        normalized_resolution_count,
    )


def _detect_resolution_column(fieldnames):
    normalized_to_raw = {}
    for fieldname in fieldnames:
        normalized_to_raw[_normalize_header(fieldname)] = fieldname

    for candidate in RESOLUTION_COLUMN_CANDIDATES:
        raw_fieldname = normalized_to_raw.get(candidate)
        if raw_fieldname:
            return raw_fieldname

    raise LegacyUserSelectionsImportValidationError(
        [
            'CSV file is missing a manual resolution column. Expected one of: '
            + ', '.join(RESOLUTION_COLUMN_CANDIDATES)
            + '.'
        ]
    )


def _detect_optional_column(fieldnames, candidates):
    normalized_to_raw = {}
    for fieldname in fieldnames:
        normalized_to_raw[_normalize_header(fieldname)] = fieldname

    for candidate in candidates:
        raw_fieldname = normalized_to_raw.get(candidate)
        if raw_fieldname:
            return raw_fieldname
    return None


def _normalize_header(raw_value):
    return ''.join(character for character in str(raw_value or '').strip().lower() if character.isalnum() or character == '_')


def _normalize_section_code(raw_value):
    normalized = str(raw_value or '').strip().lower()
    return SECTION_CODE_NORMALIZATION.get(normalized, normalized)


def _parse_manual_override(raw_value):
    normalized = str(raw_value or '').strip().lower()
    return normalized in TRUE_VALUES


def _build_manual_override_note_metadata(row):
    if not row.manual_override:
        return None
    return (
        'manual_override=true',
        f'manual_override_section={row.resolved_section_code}',
        f'manual_override_reason={row.manual_override_reason}',
    )


def _match_planned_selection(*, row, planned_monthly_selections):
    for planned_selection in planned_monthly_selections:
        if planned_selection.month == row.month and planned_selection.selection_kind == row.selection_kind:
            return planned_selection
    return None


def _plan_matches_legacy_identity(*, plan, legacy_userselection_id, selection_kind, month):
    expected_note = _build_plan_note(
        existing_notes='',
        planned_selection=type('PlannedSelectionStub', (), {'selection_kind': selection_kind, 'month': month})(),
        legacy_selection_id=legacy_userselection_id,
    )
    return expected_note in (plan.notes or '')
