import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from scheduling.models import User, UserRole
from scheduling.use_cases import activate_student_monthly_access


LEGACY_NOTES_START = '[legacy-user-import]'
LEGACY_NOTES_END = '[/legacy-user-import]'
LEGACY_SOURCE_NAME = 'eunoia.users.json'
LEGACY_ROLE_MAP = {
    'admin': UserRole.ADMIN,
    'usuario': UserRole.STUDENT,
    'student': UserRole.STUDENT,
}


class LegacyUserImportValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('\n'.join(errors))


@dataclass(frozen=True)
class ParsedLegacyUser:
    source_index: int
    legacy_id: str
    email: str
    first_name: str
    last_name: str
    phone: str
    role: str
    paid: bool
    weekly_days: int | None
    registered_at: datetime | None
    paid_at: datetime | None
    has_reset_token: bool


@dataclass(frozen=True)
class LegacyUserImportResult:
    created_count: int
    updated_count: int
    password_reset_count: int
    activated_access_count: int

    @property
    def processed_count(self):
        return self.created_count + self.updated_count


def import_legacy_users_from_json(*, json_path, reset_passwords=False, dry_run=False):
    records = load_legacy_users(json_path)
    existing_users = {
        user.email: user
        for user in User.objects.filter(email__in=[record.email for record in records])
    }

    created_count = 0
    updated_count = 0
    password_reset_count = 0
    activated_access_count = 0

    with transaction.atomic():
        for record in records:
            user = existing_users.get(record.email)
            is_new_user = user is None
            generated_password = build_legacy_temporary_password(record)

            if is_new_user:
                user = User(
                    email=record.email,
                    first_name=record.first_name,
                    last_name=record.last_name,
                    phone=record.phone,
                    role=record.role,
                    is_active=True,
                    is_staff=record.role == UserRole.ADMIN,
                )
                user.primary_section = None
                user.notes = merge_legacy_notes('', record)
                user.set_initial_password(generated_password, require_password_change=True)
                user.save()
                _restore_legacy_created_at(user=user, registered_at=record.registered_at)

                created_count += 1
                password_reset_count += 1
                existing_users[user.email] = user
            else:
                changed_fields = []
                for field_name, new_value in (
                    ('first_name', record.first_name),
                    ('last_name', record.last_name),
                    ('phone', record.phone),
                    ('role', record.role),
                ):
                    if getattr(user, field_name) != new_value:
                        setattr(user, field_name, new_value)
                        changed_fields.append(field_name)

                is_staff = record.role == UserRole.ADMIN or user.is_superuser
                if user.is_staff != is_staff:
                    user.is_staff = is_staff
                    changed_fields.append('is_staff')

                merged_notes = merge_legacy_notes(user.notes, record)
                if user.notes != merged_notes:
                    user.notes = merged_notes
                    changed_fields.append('notes')

                if reset_passwords:
                    user.set_initial_password(generated_password, require_password_change=True)
                    changed_fields.extend(['password', 'must_change_password', 'temporary_password_set_at'])
                    password_reset_count += 1

                if changed_fields:
                    user.save(update_fields=sorted(set(changed_fields + ['updated_at'])))
                updated_count += 1

            if record.role == UserRole.STUDENT and record.paid_at is not None:
                access_change = activate_student_monthly_access(
                    student=user,
                    month=record.paid_at.date(),
                    record_audit=False,
                )
                if access_change.changed:
                    activated_access_count += 1

        if dry_run:
            transaction.set_rollback(True)

    return LegacyUserImportResult(
        created_count=created_count,
        updated_count=updated_count,
        password_reset_count=password_reset_count,
        activated_access_count=activated_access_count,
    )


def load_legacy_users(json_path):
    path = Path(json_path)
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise LegacyUserImportValidationError([f'JSON file not found: {path}']) from exc
    except OSError as exc:
        raise LegacyUserImportValidationError([f'Could not read JSON file: {exc}']) from exc
    except json.JSONDecodeError as exc:
        raise LegacyUserImportValidationError([f'Invalid JSON file: {exc}']) from exc

    if not isinstance(payload, list):
        raise LegacyUserImportValidationError(['The JSON file must contain a top-level array of users.'])

    records = []
    seen_emails = set()
    errors = []

    for index, raw_user in enumerate(payload, start=1):
        entry_errors = []
        if not isinstance(raw_user, dict):
            errors.append(f'Entry {index}: expected an object.')
            continue

        legacy_id = _extract_legacy_id(raw_user.get('_id'))
        email = User.objects.normalize_email(str(raw_user.get('email') or '').strip())
        first_name = str(raw_user.get('nombre') or '').strip()
        last_name = str(raw_user.get('apellido') or '').strip()
        phone = str(raw_user.get('celular') or '').strip()
        role = _map_legacy_role(raw_user.get('rol'))
        paid = bool(raw_user.get('pago'))
        weekly_days = raw_user.get('diasSemanales')

        if not legacy_id:
            entry_errors.append(f'Entry {index}: missing legacy _id.$oid.')
        if not email:
            entry_errors.append(f'Entry {index}: email is required.')
        elif email in seen_emails:
            entry_errors.append(f'Entry {index}: duplicate email within the same file: {email}.')
        else:
            seen_emails.add(email)
            try:
                validate_email(email)
            except DjangoValidationError:
                entry_errors.append(f'Entry {index}: invalid email "{email}".')

        if not first_name:
            entry_errors.append(f'Entry {index}: nombre is required.')
        if not last_name:
            entry_errors.append(f'Entry {index}: apellido is required.')
        if role is None:
            entry_errors.append(f'Entry {index}: unsupported rol "{raw_user.get("rol")}".')

        try:
            registered_at = _parse_legacy_datetime(raw_user.get('fechaRegistro'))
        except ValueError as exc:
            entry_errors.append(f'Entry {index}: invalid fechaRegistro. {exc}')
            registered_at = None

        try:
            paid_at = _parse_legacy_datetime(raw_user.get('fechaPago'))
        except ValueError as exc:
            entry_errors.append(f'Entry {index}: invalid fechaPago. {exc}')
            paid_at = None

        if paid and paid_at is None:
            entry_errors.append(f'Entry {index}: pago=true requires fechaPago.')

        if entry_errors:
            errors.extend(entry_errors)
            continue

        records.append(
            ParsedLegacyUser(
                source_index=index,
                legacy_id=legacy_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                paid=paid,
                weekly_days=weekly_days if isinstance(weekly_days, int) else None,
                registered_at=registered_at,
                paid_at=paid_at,
                has_reset_token=bool(raw_user.get('resetPasswordToken')),
            )
        )

    if errors:
        raise LegacyUserImportValidationError(errors)

    return records


def build_legacy_temporary_password(record):
    digest = hashlib.sha256(
        f'{settings.SECRET_KEY}|legacy-user-import|{record.legacy_id}|{record.email}'.encode('utf-8')
    ).hexdigest()
    password = f'Eu!{digest[:8]}-{digest[8:16]}a1'
    password_validation.validate_password(password)
    return password


def merge_legacy_notes(existing_notes, record):
    base_notes = (existing_notes or '').strip()
    start_index = base_notes.find(LEGACY_NOTES_START)
    end_index = base_notes.find(LEGACY_NOTES_END)
    if start_index != -1 and end_index != -1 and end_index > start_index:
        managed_prefix = base_notes[:start_index].rstrip()
        managed_suffix = base_notes[end_index + len(LEGACY_NOTES_END):].strip()
        base_notes = '\n\n'.join(bit for bit in (managed_prefix, managed_suffix) if bit)

    block_lines = [
        LEGACY_NOTES_START,
        f'source={LEGACY_SOURCE_NAME}',
        f'legacy_user_id={record.legacy_id}',
        f'legacy_weekly_days={record.weekly_days if record.weekly_days is not None else ""}',
        f'legacy_paid={str(record.paid).lower()}',
        f'legacy_paid_at={record.paid_at.isoformat() if record.paid_at is not None else ""}',
        f'legacy_registered_at={record.registered_at.isoformat() if record.registered_at is not None else ""}',
        f'legacy_reset_token_present={str(record.has_reset_token).lower()}',
        LEGACY_NOTES_END,
    ]
    managed_block = '\n'.join(block_lines)

    if not base_notes:
        return managed_block
    return f'{base_notes}\n\n{managed_block}'


def _restore_legacy_created_at(*, user, registered_at):
    if registered_at is None:
        return
    User.objects.filter(pk=user.pk).update(created_at=registered_at)


def _extract_legacy_id(raw_id):
    if isinstance(raw_id, dict):
        return str(raw_id.get('$oid') or '').strip()
    return ''


def _map_legacy_role(raw_role):
    role = str(raw_role or '').strip().lower()
    return LEGACY_ROLE_MAP.get(role)


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
