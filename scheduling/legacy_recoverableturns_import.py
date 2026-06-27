import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from scheduling.legacy_userselections_import import build_confirmed_section_candidates_by_weekday_and_time
from scheduling.models import RecoveryCredit, RecoveryCreditSource, RecoveryCreditStatus, Section, User, Weekday


LEGACY_RECOVERABLETURNS_NOTES_START = '[legacy-recoverableturns-import]'
LEGACY_RECOVERABLETURNS_NOTES_END = '[/legacy-recoverableturns-import]'
LEGACY_RECOVERABLETURNS_SOURCE = 'eunoia.recoverableturns.json'
LEGACY_RECOVERABLETURNS_REVOCATION_NOTE = 'Legacy import revoked: current activity is outside the valid ambiguous section set.'
LEGACY_RECOVERABLETURN_ID_PATTERN = re.compile(
    r'^legacy_recoverableturn_id=(?P<legacy_id>[^\n]+)$',
    re.MULTILINE,
)
LEGACY_USER_ID_PATTERN = re.compile(r'^legacy_user_id=(?P<legacy_id>[^\n]+)$', re.MULTILINE)
LEGACY_DAY_TO_WEEKDAY = {
    'lunes': Weekday.MONDAY,
    'martes': Weekday.TUESDAY,
    'miercoles': Weekday.WEDNESDAY,
    'jueves': Weekday.THURSDAY,
    'viernes': Weekday.FRIDAY,
    'sabado': Weekday.SATURDAY,
    'domingo': Weekday.SUNDAY,
}


class LegacyRecoverableTurnsImportValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('\n'.join(errors))


@dataclass(frozen=True)
class ParsedLegacyRecoverableTurn:
    source_index: int
    legacy_turn_id: str
    legacy_user_id: str
    original_day: str
    original_hour: str
    cancelled_week: datetime
    recovered: bool
    recovery_date: datetime | None
    assigned_day: str | None
    assigned_hour: str | None
    candidate_section_codes: tuple[str, ...]


@dataclass(frozen=True)
class LegacyRecoverableTurnsImportResult:
    total_records: int
    matched_user_count: int
    created_count: int
    unchanged_count: int
    resolved_by_current_activity_count: int
    revoked_invalid_section_count: int
    skipped_missing_user_count: int
    skipped_ambiguous_section_count: int
    skipped_missing_mapping_count: int
    skipped_inconsistent_state_count: int
    imported_available_count: int
    imported_expired_count: int
    imported_used_count: int


def import_legacy_recoverableturns_from_json(*, json_path, dry_run=False):
    records = load_legacy_recoverableturns(json_path)
    reference_date = timezone.localdate()
    users_by_legacy_id = {
        legacy_id: user
        for user in User.objects.filter(role='student').select_related('primary_section')
        for legacy_id in [_extract_user_legacy_id(user.notes)]
        if legacy_id
    }
    sections_by_code = {section.code: section for section in Section.objects.all()}
    existing_credits_by_legacy_id = {
        legacy_id: credit
        for credit in RecoveryCredit.objects.filter(source=RecoveryCreditSource.MANUAL).select_related('student', 'section')
        for legacy_id in [_extract_credit_legacy_id(credit.notes)]
        if legacy_id
    }

    matched_user_count = 0
    created_count = 0
    unchanged_count = 0
    resolved_by_current_activity_count = 0
    revoked_invalid_section_count = 0
    skipped_missing_user_count = 0
    skipped_ambiguous_section_count = 0
    skipped_missing_mapping_count = 0
    skipped_inconsistent_state_count = 0
    imported_available_count = 0
    imported_expired_count = 0
    imported_used_count = 0

    with transaction.atomic():
        revoked_invalid_section_count = _revoke_invalid_ambiguous_existing_credits(
            records=records,
            users_by_legacy_id=users_by_legacy_id,
            existing_credits_by_legacy_id=existing_credits_by_legacy_id,
            sections_by_code=sections_by_code,
            reference_date=reference_date,
        )
        for record in records:
            user = users_by_legacy_id.get(record.legacy_user_id)
            if user is None:
                skipped_missing_user_count += 1
                continue

            matched_user_count += 1

            if not _has_consistent_state(record):
                skipped_inconsistent_state_count += 1
                continue

            section, resolved_by_current_activity = _resolve_section_for_import(
                record=record,
                user=user,
                sections_by_code=sections_by_code,
                reference_date=reference_date,
            )
            if section is None:
                if not record.candidate_section_codes:
                    skipped_missing_mapping_count += 1
                    continue
                skipped_ambiguous_section_count += 1
                continue

            if resolved_by_current_activity:
                resolved_by_current_activity_count += 1

            credit_spec = _build_credit_spec(record=record, user=user, section=section)
            existing_credit = existing_credits_by_legacy_id.get(record.legacy_turn_id)

            if existing_credit is not None:
                if _credit_matches_spec(existing_credit=existing_credit, credit_spec=credit_spec):
                    unchanged_count += 1
                else:
                    raise LegacyRecoverableTurnsImportValidationError([
                        (
                            'Existing recovery credit imported from legacy recoverable turns '
                            f'conflicts with current data for legacy id {record.legacy_turn_id}.'
                        )
                    ])
            else:
                credit = RecoveryCredit(**credit_spec)
                credit.save(force_insert=True)
                existing_credits_by_legacy_id[record.legacy_turn_id] = credit
                created_count += 1

            status = credit_spec['status']
            if status == RecoveryCreditStatus.USED:
                imported_used_count += 1
            elif status == RecoveryCreditStatus.EXPIRED:
                imported_expired_count += 1
            else:
                imported_available_count += 1

        if dry_run:
            transaction.set_rollback(True)

    return LegacyRecoverableTurnsImportResult(
        total_records=len(records),
        matched_user_count=matched_user_count,
        created_count=created_count,
        unchanged_count=unchanged_count,
        resolved_by_current_activity_count=resolved_by_current_activity_count,
        revoked_invalid_section_count=revoked_invalid_section_count,
        skipped_missing_user_count=skipped_missing_user_count,
        skipped_ambiguous_section_count=skipped_ambiguous_section_count,
        skipped_missing_mapping_count=skipped_missing_mapping_count,
        skipped_inconsistent_state_count=skipped_inconsistent_state_count,
        imported_available_count=imported_available_count,
        imported_expired_count=imported_expired_count,
        imported_used_count=imported_used_count,
    )


def load_legacy_recoverableturns(json_path):
    path = Path(json_path)
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise LegacyRecoverableTurnsImportValidationError([f'JSON file not found: {path}']) from exc
    except OSError as exc:
        raise LegacyRecoverableTurnsImportValidationError([f'Could not read JSON file: {exc}']) from exc
    except json.JSONDecodeError as exc:
        raise LegacyRecoverableTurnsImportValidationError([f'Invalid JSON file: {exc}']) from exc

    if not isinstance(payload, list):
        raise LegacyRecoverableTurnsImportValidationError(
            ['The JSON file must contain a top-level array of recoverable turns.']
        )

    section_candidates_by_slot = build_confirmed_section_candidates_by_weekday_and_time()
    records = []
    errors = []
    seen_legacy_turn_ids = set()

    for index, raw_record in enumerate(payload, start=1):
        if not isinstance(raw_record, dict):
            errors.append(f'Entry {index}: expected an object.')
            continue

        legacy_turn_id = _extract_legacy_id(raw_record.get('_id'))
        legacy_user_id = _extract_legacy_id(raw_record.get('user'))
        original_day = str(raw_record.get('originalDay') or '').strip()
        original_hour = str(raw_record.get('originalHour') or '').strip()
        recovered = raw_record.get('recovered')
        assigned_day = _clean_optional_text(raw_record.get('assignedDay'))
        assigned_hour = _clean_optional_text(raw_record.get('assignedHour'))

        entry_errors = []
        if not legacy_turn_id:
            entry_errors.append(f'Entry {index}: missing _id.$oid.')
        elif legacy_turn_id in seen_legacy_turn_ids:
            entry_errors.append(f'Entry {index}: duplicate _id.$oid {legacy_turn_id}.')
        else:
            seen_legacy_turn_ids.add(legacy_turn_id)

        if not legacy_user_id:
            entry_errors.append(f'Entry {index}: missing user.$oid.')
        if not original_day:
            entry_errors.append(f'Entry {index}: originalDay is required.')
        if not original_hour:
            entry_errors.append(f'Entry {index}: originalHour is required.')
        if not isinstance(recovered, bool):
            entry_errors.append(f'Entry {index}: recovered must be a boolean.')

        try:
            cancelled_week = _parse_legacy_datetime(raw_record.get('cancelledWeek'))
        except ValueError as exc:
            entry_errors.append(f'Entry {index}: invalid cancelledWeek. {exc}')
            cancelled_week = None

        try:
            recovery_date = _parse_legacy_datetime(raw_record.get('recoveryDate'))
        except ValueError as exc:
            entry_errors.append(f'Entry {index}: invalid recoveryDate. {exc}')
            recovery_date = None

        candidate_section_codes = ()
        if original_day and original_hour:
            try:
                weekday, start_time = _parse_legacy_slot(day=original_day, hour=original_hour)
            except ValueError as exc:
                entry_errors.append(f'Entry {index}: {exc}')
            else:
                candidate_section_codes = tuple(section_candidates_by_slot.get((weekday, start_time), ()))

        if assigned_day and not assigned_hour:
            entry_errors.append(f'Entry {index}: assignedHour is required when assignedDay is present.')
        if assigned_hour and not assigned_day:
            entry_errors.append(f'Entry {index}: assignedDay is required when assignedHour is present.')
        if assigned_day and assigned_hour:
            try:
                _parse_legacy_slot(day=assigned_day, hour=assigned_hour)
            except ValueError as exc:
                entry_errors.append(f'Entry {index}: assigned slot is invalid. {exc}')

        if entry_errors:
            errors.extend(entry_errors)
            continue

        records.append(
            ParsedLegacyRecoverableTurn(
                source_index=index,
                legacy_turn_id=legacy_turn_id,
                legacy_user_id=legacy_user_id,
                original_day=original_day,
                original_hour=original_hour,
                cancelled_week=cancelled_week,
                recovered=recovered,
                recovery_date=recovery_date,
                assigned_day=assigned_day,
                assigned_hour=assigned_hour,
                candidate_section_codes=candidate_section_codes,
            )
        )

    if errors:
        raise LegacyRecoverableTurnsImportValidationError(errors)

    return records


def _build_credit_spec(*, record, user, section):
    status = RecoveryCreditStatus.USED if record.recovered else RecoveryCreditStatus.AVAILABLE
    credit = RecoveryCredit(
        student=user,
        section=section,
        source=RecoveryCreditSource.MANUAL,
        status=status,
        expires_at=record.cancelled_week.date(),
    )
    credit.set_expiration_date(reference_date=record.cancelled_week.date())

    if record.recovered:
        credit.status = RecoveryCreditStatus.USED
        credit.used_at = record.recovery_date
    elif credit.is_overdue(on_date=timezone.localdate()):
        credit.status = RecoveryCreditStatus.EXPIRED

    credit.notes = _build_credit_note(record=record, existing_notes='')

    return {
        'student': credit.student,
        'section': credit.section,
        'source': credit.source,
        'status': credit.status,
        'expires_at': credit.expires_at,
        'used_at': credit.used_at,
        'notes': credit.notes,
    }


def _resolve_section_for_import(*, record, user, sections_by_code, reference_date):
    if not record.candidate_section_codes:
        return None, False

    if len(record.candidate_section_codes) == 1:
        return sections_by_code.get(record.candidate_section_codes[0]), False

    if record.recovered:
        return None, False

    preview_credit = RecoveryCredit(
        student=user,
        section=user.primary_section,
        source=RecoveryCreditSource.MANUAL,
        status=RecoveryCreditStatus.AVAILABLE,
        expires_at=record.cancelled_week.date(),
    )
    preview_credit.set_expiration_date(reference_date=record.cancelled_week.date())
    if preview_credit.is_overdue(on_date=reference_date):
        return None, False

    current_section = _resolve_current_activity_section(user=user, reference_date=reference_date)
    if current_section is not None and current_section.code in record.candidate_section_codes:
        return current_section, True

    return None, False


def _revoke_invalid_ambiguous_existing_credits(*, records, users_by_legacy_id, existing_credits_by_legacy_id, sections_by_code, reference_date):
    records_by_legacy_turn_id = {record.legacy_turn_id: record for record in records}
    revoked_count = 0

    for legacy_turn_id, credit in existing_credits_by_legacy_id.items():
        if credit.status != RecoveryCreditStatus.AVAILABLE:
            continue

        record = records_by_legacy_turn_id.get(legacy_turn_id)
        if record is None or len(record.candidate_section_codes) <= 1:
            continue

        user = users_by_legacy_id.get(record.legacy_user_id)
        if user is None or not _has_consistent_state(record):
            continue

        resolved_section, _ = _resolve_section_for_import(
            record=record,
            user=user,
            sections_by_code=sections_by_code,
            reference_date=reference_date,
        )
        if resolved_section is not None:
            continue
        if credit.section.code in record.candidate_section_codes:
            continue

        credit.status = RecoveryCreditStatus.REVOKED
        credit.notes = _append_revocation_note(
            existing_notes=credit.notes,
            record=record,
            credit=credit,
        )
        credit.save(update_fields=['status', 'notes', 'updated_at'])
        revoked_count += 1

    return revoked_count


def _append_revocation_note(*, existing_notes, record, credit):
    suffix = (
        f'{LEGACY_RECOVERABLETURNS_REVOCATION_NOTE} '
        f'Current credit section `{credit.section.code}` is outside {sorted(record.candidate_section_codes)}.'
    )
    base_notes = (existing_notes or '').strip()
    if suffix in base_notes:
        return base_notes
    if not base_notes:
        return suffix
    return f'{base_notes}\n\n{suffix}'


def _resolve_current_activity_section(*, user, reference_date):
    effective_plan = user.get_effective_monthly_plan_for(reference_date)
    if effective_plan is not None:
        return effective_plan.section
    return user.primary_section


def _build_credit_note(*, record, existing_notes):
    base_notes = (existing_notes or '').strip()
    start_index = base_notes.find(LEGACY_RECOVERABLETURNS_NOTES_START)
    end_index = base_notes.find(LEGACY_RECOVERABLETURNS_NOTES_END)
    if start_index != -1 and end_index != -1 and end_index > start_index:
        managed_prefix = base_notes[:start_index].rstrip()
        managed_suffix = base_notes[end_index + len(LEGACY_RECOVERABLETURNS_NOTES_END):].strip()
        base_notes = '\n\n'.join(bit for bit in (managed_prefix, managed_suffix) if bit)

    block_lines = [
        LEGACY_RECOVERABLETURNS_NOTES_START,
        f'source={LEGACY_RECOVERABLETURNS_SOURCE}',
        f'legacy_recoverableturn_id={record.legacy_turn_id}',
        f'legacy_user_id={record.legacy_user_id}',
        f'legacy_original_day={record.original_day}',
        f'legacy_original_hour={record.original_hour}',
        f'legacy_cancelled_week={record.cancelled_week.isoformat()}',
        f'legacy_recovered={str(record.recovered).lower()}',
        f'legacy_recovery_date={record.recovery_date.isoformat() if record.recovery_date is not None else ""}',
        f'legacy_assigned_day={record.assigned_day or ""}',
        f'legacy_assigned_hour={record.assigned_hour or ""}',
        LEGACY_RECOVERABLETURNS_NOTES_END,
    ]
    managed_block = '\n'.join(block_lines)

    if not base_notes:
        return managed_block
    return f'{base_notes}\n\n{managed_block}'


def _credit_matches_spec(*, existing_credit, credit_spec):
    return (
        existing_credit.student_id == credit_spec['student'].pk
        and existing_credit.section_id == credit_spec['section'].pk
        and existing_credit.source == credit_spec['source']
        and existing_credit.status == credit_spec['status']
        and existing_credit.expires_at == credit_spec['expires_at']
        and existing_credit.used_at == credit_spec['used_at']
        and existing_credit.notes == credit_spec['notes']
    )


def _has_consistent_state(record):
    has_assigned_slot = record.assigned_day is not None and record.assigned_hour is not None
    if record.recovered:
        return record.recovery_date is not None and has_assigned_slot
    return record.recovery_date is None and not has_assigned_slot


def _extract_credit_legacy_id(notes):
    if not notes:
        return ''
    match = LEGACY_RECOVERABLETURN_ID_PATTERN.search(notes)
    return match.group('legacy_id').strip() if match else ''


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


def _parse_legacy_slot(*, day, hour):
    normalized_day = _normalize_legacy_day(day)
    weekday = LEGACY_DAY_TO_WEEKDAY.get(normalized_day)
    if weekday is None:
        raise ValueError(f'unsupported day "{day}".')

    try:
        start_time = time.fromisoformat(hour)
    except ValueError as exc:
        raise ValueError(f'invalid hour "{hour}".') from exc

    return weekday, start_time


def _normalize_legacy_day(raw_day):
    normalized = unicodedata.normalize('NFKD', str(raw_day or '').strip().lower())
    return ''.join(character for character in normalized if not unicodedata.combining(character))


def _clean_optional_text(raw_value):
    value = str(raw_value or '').strip()
    return value or None
