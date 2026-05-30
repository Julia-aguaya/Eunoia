import csv
from dataclasses import dataclass

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction

from .application.onboarding import (
    create_student_onboarding,
    get_default_temporary_password,
    resolve_temporary_password,
)
from .models import Section, User, UserRole


EXPECTED_STUDENT_IMPORT_COLUMNS = (
    'email',
    'first_name',
    'last_name',
    'primary_section',
    'role',
    'is_active',
    'must_change_password',
    'temporary_password',
    'phone',
    'notes',
)

REQUIRED_STUDENT_IMPORT_COLUMNS = (
    'email',
    'first_name',
    'last_name',
    'primary_section',
)

TRUE_VALUES = {'1', 'true', 'yes', 'si', 'on'}
FALSE_VALUES = {'0', 'false', 'no', 'off'}


class StudentImportValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('\n'.join(errors))


@dataclass(frozen=True)
class ParsedStudentImportRow:
    row_number: int
    email: str
    first_name: str
    last_name: str
    primary_section: Section
    role: str | None
    is_active: bool | None
    must_change_password: bool | None
    temporary_password: str | None
    phone: str
    notes: str


@dataclass(frozen=True)
class StudentImportResult:
    created_count: int
    updated_count: int

    @property
    def processed_count(self):
        return self.created_count + self.updated_count


def import_students_from_csv(file_obj):
    rows = _parse_student_rows(file_obj)
    if not rows:
        raise StudentImportValidationError(['The CSV file does not contain data rows.'])

    default_temporary_password = get_default_temporary_password()
    existing_users = {
        user.email: user
        for user in User.objects.filter(email__in=[row.email for row in rows]).select_related('primary_section')
    }
    _validate_student_rows(rows, existing_users=existing_users, default_temporary_password=default_temporary_password)

    created_count = 0
    updated_count = 0

    with transaction.atomic():
        for row in rows:
            user = existing_users.get(row.email)
            is_new_user = user is None
            role = row.role or (user.role if user is not None else UserRole.STUDENT)
            require_password_change = row.must_change_password if row.must_change_password is not None else True
            if is_new_user:
                user = create_student_onboarding(
                    email=row.email,
                    first_name=row.first_name,
                    last_name=row.last_name,
                    primary_section=row.primary_section,
                    phone=row.phone,
                    notes=row.notes,
                    role=role,
                    temporary_password=row.temporary_password,
                    must_change_password=require_password_change,
                    is_active=row.is_active if row.is_active is not None else True,
                    is_staff=role == UserRole.ADMIN,
                )
                created_count += 1
                existing_users[user.email] = user
                continue

            assert user is not None
            user.first_name = row.first_name
            user.last_name = row.last_name
            user.primary_section = row.primary_section
            user.role = role
            user.phone = row.phone
            user.notes = row.notes
            if row.is_active is not None:
                user.is_active = row.is_active

            if user.role == UserRole.ADMIN:
                user.is_staff = True
            elif not user.is_superuser:
                user.is_staff = False

            if row.temporary_password:
                user.set_initial_password(
                    resolve_temporary_password(row.temporary_password),
                    require_password_change=require_password_change,
                )

            user.save()
            updated_count += 1

    return StudentImportResult(created_count=created_count, updated_count=updated_count)


def _parse_student_rows(file_obj):
    reader = csv.DictReader(file_obj)
    if reader.fieldnames is None:
        raise StudentImportValidationError(['The CSV file must include a header row.'])

    normalized_fieldnames = [_normalize_header_name(field_name) for field_name in reader.fieldnames]
    duplicate_headers = sorted({field_name for field_name in normalized_fieldnames if normalized_fieldnames.count(field_name) > 1})
    if duplicate_headers:
        raise StudentImportValidationError([f'Duplicate CSV columns: {", ".join(duplicate_headers)}'])

    reader.fieldnames = normalized_fieldnames
    _validate_headers(normalized_fieldnames)

    sections_by_code = {section.code: section for section in Section.objects.all()}
    valid_roles = {choice for choice, _label in UserRole.choices}
    rows = []
    seen_emails = set()
    errors = []

    for row_number, raw_row in enumerate(reader, start=2):
        normalized_row = {key: (value or '').strip() for key, value in raw_row.items()}
        if not any(normalized_row.values()):
            continue

        email = User.objects.normalize_email(normalized_row['email'])
        if not email:
            errors.append(f'Row {row_number}: email is required.')
        elif email in seen_emails:
            errors.append(f'Row {row_number}: duplicated email within the same file: {email}.')
        else:
            seen_emails.add(email)

        for required_column in ('first_name', 'last_name', 'primary_section'):
            if not normalized_row[required_column]:
                errors.append(f'Row {row_number}: {required_column} is required.')

        section_code = normalized_row['primary_section'].lower()
        section = sections_by_code.get(section_code)
        if normalized_row['primary_section'] and section is None:
            errors.append(
                f'Row {row_number}: unknown primary_section "{normalized_row["primary_section"]}". '
                'Use one of: reformer_arriba, reformer_abajo, cadillac.'
            )

        role = normalized_row.get('role', '').lower() or None
        if role is not None and role not in valid_roles:
            errors.append(f'Row {row_number}: invalid role "{role}". Use student or admin.')

        try:
            is_active = _parse_boolean(normalized_row.get('is_active'))
        except StudentImportValidationError as exc:
            errors.extend([f'Row {row_number}: {message}' for message in exc.errors])
            is_active = None

        try:
            must_change_password = _parse_boolean(normalized_row.get('must_change_password'))
        except StudentImportValidationError as exc:
            errors.extend([f'Row {row_number}: {message}' for message in exc.errors])
            must_change_password = None

        if email:
            try:
                validate_email(email)
            except DjangoValidationError:
                errors.append(f'Row {row_number}: invalid email "{email}".')

        rows.append(
            ParsedStudentImportRow(
                row_number=row_number,
                email=email,
                first_name=normalized_row['first_name'],
                last_name=normalized_row['last_name'],
                primary_section=section,
                role=role,
                is_active=is_active,
                must_change_password=must_change_password,
                temporary_password=normalized_row.get('temporary_password') or None,
                phone=normalized_row.get('phone', ''),
                notes=normalized_row.get('notes', ''),
            )
        )

    if errors:
        raise StudentImportValidationError(errors)

    return rows


def _validate_student_rows(rows, *, existing_users, default_temporary_password):
    errors = []
    requires_default_password = any(
        row.temporary_password is None and row.email not in existing_users
        for row in rows
    )

    if requires_default_password:
        try:
            resolve_temporary_password(default_temporary_password)
        except DjangoValidationError as exc:
            errors.extend([f'Default temporary password is invalid: {message}' for message in exc.messages])

    for row in rows:
        try:
            if row.temporary_password:
                resolve_temporary_password(row.temporary_password)
            elif row.email not in existing_users:
                resolve_temporary_password(default_temporary_password)
        except DjangoValidationError as exc:
            errors.extend([f'Row {row.row_number}: invalid temporary_password. {message}' for message in exc.messages])

    if errors:
        raise StudentImportValidationError(errors)


def _validate_headers(fieldnames):
    actual_columns = set(fieldnames)
    missing_columns = sorted(set(REQUIRED_STUDENT_IMPORT_COLUMNS) - actual_columns)
    unexpected_columns = sorted(actual_columns - set(EXPECTED_STUDENT_IMPORT_COLUMNS))
    errors = []

    if missing_columns:
        errors.append(f'Missing required CSV columns: {", ".join(missing_columns)}.')
    if unexpected_columns:
        errors.append(
            f'Unexpected CSV columns: {", ".join(unexpected_columns)}. '
            f'Expected columns are: {", ".join(EXPECTED_STUDENT_IMPORT_COLUMNS)}.'
        )

    if errors:
        raise StudentImportValidationError(errors)


def _normalize_header_name(value):
    return (value or '').strip().lower().lstrip('\ufeff')


def _parse_boolean(raw_value):
    if raw_value is None:
        return None

    value = raw_value.strip().lower()
    if value == '':
        return None
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False

    raise StudentImportValidationError([
        f'Invalid boolean value "{raw_value}". Use true/false, yes/no, si/no, 1/0 or leave it blank.'
    ])
