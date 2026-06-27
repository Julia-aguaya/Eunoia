from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from scheduling.legacy_recoverableturns_import import (  # noqa: E402
    _extract_user_legacy_id,
    _has_consistent_state,
    load_legacy_recoverableturns,
)
from scheduling.models import User  # noqa: E402


DEFAULT_JSON_PATH = Path('eunoia.recoverableturns.json')
DEFAULT_LEGACY_USERS_PATH = Path('eunoia.users.json')
DEFAULT_MARKDOWN_OUTPUT = Path('docs/reports/legacy_recoverableturns_blocked_report.md')
DEFAULT_JSON_OUTPUT = Path('docs/reports/legacy_recoverableturns_blocked_report.json')
DEFAULT_CSV_OUTPUT = Path('docs/reports/legacy_recoverableturns_blocked_report.csv')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate a manual review report for legacy recoverable turns blocked by the partial import.'
    )
    parser.add_argument('--json-path', type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument('--legacy-users-path', type=Path, default=DEFAULT_LEGACY_USERS_PATH)
    parser.add_argument('--markdown-output', type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument('--json-output', type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument('--csv-output', type=Path, default=DEFAULT_CSV_OUTPUT)
    return parser.parse_args()


def load_legacy_users_by_id(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    by_id = {}
    for raw_user in payload:
        if not isinstance(raw_user, dict):
            continue
        raw_id = raw_user.get('_id') or {}
        legacy_id = str(raw_id.get('$oid') or '').strip() if isinstance(raw_id, dict) else ''
        if not legacy_id:
            continue
        first_name = str(raw_user.get('nombre') or '').strip()
        last_name = str(raw_user.get('apellido') or '').strip()
        full_name = ' '.join(bit for bit in (first_name, last_name) if bit).strip()
        by_id[legacy_id] = {
            'legacy_user_email': str(raw_user.get('email') or '').strip(),
            'legacy_user_name': full_name,
        }
    return by_id


def classify_blocked_case(*, record, user, legacy_user):
    possible_sections = list(record.candidate_section_codes)

    if user is None:
        return 'orphan_user', 'No current student matches this legacy_user_id.', possible_sections
    if not _has_consistent_state(record):
        if record.recovered:
            detail = 'Recovered=true but assigned slot or recoveryDate is missing.'
        else:
            detail = 'Recovered=false but assigned slot or recoveryDate is unexpectedly present.'
        return 'inconsistent_state', detail, possible_sections
    if not record.candidate_section_codes:
        return 'missing_section_mapping', 'Original day/hour has no confirmed section mapping.', possible_sections
    if len(record.candidate_section_codes) != 1:
        return 'ambiguous_section', 'Original day/hour maps to more than one possible section.', possible_sections
    return None


def collect_blocker_flags(*, record, user):
    flags = []
    if user is None:
        flags.append('orphan_user')
    if not _has_consistent_state(record):
        flags.append('inconsistent_state')
    if not record.candidate_section_codes:
        flags.append('missing_section_mapping')
    elif len(record.candidate_section_codes) != 1:
        flags.append('ambiguous_section')
    return flags


def build_cases(*, json_path: Path, legacy_users_path: Path):
    records = load_legacy_recoverableturns(json_path)
    legacy_users_by_id = load_legacy_users_by_id(legacy_users_path)
    users_by_legacy_id = {
        legacy_id: user
        for user in User.objects.filter(role='student').select_related('primary_section')
        for legacy_id in [_extract_user_legacy_id(user.notes)]
        if legacy_id
    }

    cases = []
    for record in records:
        user = users_by_legacy_id.get(record.legacy_user_id)
        legacy_user = legacy_users_by_id.get(record.legacy_user_id, {})
        classification = classify_blocked_case(record=record, user=user, legacy_user=legacy_user)
        if classification is None:
            continue

        blocking_cause, blocking_detail, possible_sections = classification
        all_blockers = collect_blocker_flags(record=record, user=user)
        current_user_name = user.get_full_name().strip() if user is not None else ''
        current_user_email = user.email if user is not None else ''
        legacy_user_name = legacy_user.get('legacy_user_name', '')
        legacy_user_email = legacy_user.get('legacy_user_email', '')

        cases.append(
            {
                'source_index': record.source_index,
                'legacy_recoverableturn_id': record.legacy_turn_id,
                'legacy_user_id': record.legacy_user_id,
                'current_user_id': user.id if user is not None else None,
                'current_user_email': current_user_email,
                'current_user_name': current_user_name,
                'current_primary_section': user.primary_section.code if user is not None and user.primary_section_id else '',
                'match_status': 'matched' if user is not None else 'orphan_user',
                'legacy_user_email': legacy_user_email,
                'legacy_user_name': legacy_user_name,
                'display_email': current_user_email or legacy_user_email,
                'display_name': current_user_name or legacy_user_name,
                'original_day': record.original_day,
                'original_hour': record.original_hour,
                'assigned_day': record.assigned_day or '',
                'assigned_hour': record.assigned_hour or '',
                'cancelled_week': record.cancelled_week.isoformat(),
                'recovery_date': record.recovery_date.isoformat() if record.recovery_date is not None else '',
                'recovered': record.recovered,
                'blocking_cause': blocking_cause,
                'blocking_detail': blocking_detail,
                'all_blockers': all_blockers,
                'secondary_blockers': [flag for flag in all_blockers if flag != blocking_cause],
                'possible_sections': possible_sections,
                'possible_sections_label': ' | '.join(possible_sections),
            }
        )

    cases.sort(
        key=lambda case: (
            case['blocking_cause'],
            (case['display_name'] or '').lower(),
            (case['display_email'] or '').lower(),
            case['legacy_user_id'],
            case['source_index'],
        )
    )
    return cases


def summarize_cases(cases: list[dict]) -> dict:
    cases_by_student = defaultdict(list)
    cases_by_cause = defaultdict(list)
    possible_sections_by_cause = defaultdict(Counter)

    for case in cases:
        student_key = case['current_user_email'] or case['legacy_user_email'] or case['legacy_user_id']
        cases_by_student[student_key].append(case)
        cases_by_cause[case['blocking_cause']].append(case)
        if case['possible_sections_label']:
            possible_sections_by_cause[case['blocking_cause']][case['possible_sections_label']] += 1

    return {
        'blocked_case_count': len(cases),
        'student_count': len(cases_by_student),
        'cause_counts': dict(sorted(Counter(case['blocking_cause'] for case in cases).items())),
        'matched_current_case_count': sum(1 for case in cases if case['match_status'] == 'matched'),
        'orphan_case_count': sum(1 for case in cases if case['blocking_cause'] == 'orphan_user'),
        'students_with_multiple_cases': sum(1 for student_cases in cases_by_student.values() if len(student_cases) > 1),
        'cases_with_secondary_blockers': sum(1 for case in cases if case['secondary_blockers']),
        'secondary_blocker_counts': dict(
            sorted(Counter(flag for case in cases for flag in case['secondary_blockers']).items())
        ),
        'possible_sections_by_cause': {
            cause: dict(sorted(counter.items()))
            for cause, counter in sorted(possible_sections_by_cause.items())
        },
        'cases_by_student': cases_by_student,
        'cases_by_cause': cases_by_cause,
    }


def serialize_case(case: dict) -> dict:
    return dict(case)


def write_csv(path: Path, cases: list[dict]) -> None:
    fieldnames = [
        'source_index',
        'legacy_recoverableturn_id',
        'legacy_user_id',
        'match_status',
        'current_user_id',
        'current_user_email',
        'current_user_name',
        'current_primary_section',
        'legacy_user_email',
        'legacy_user_name',
        'original_day',
        'original_hour',
        'assigned_day',
        'assigned_hour',
        'cancelled_week',
        'recovery_date',
        'recovered',
        'blocking_cause',
        'blocking_detail',
        'possible_sections_label',
    ]
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            writer.writerow({field: case.get(field, '') for field in fieldnames})


def write_json(path: Path, *, source_file: str, summary: dict, cases: list[dict]) -> None:
    cases_by_student_payload = []
    for student_key, student_cases in sorted(
        summary['cases_by_student'].items(),
        key=lambda item: (
            (item[1][0]['display_name'] or '').lower(),
            (item[1][0]['display_email'] or '').lower(),
            item[0],
        ),
    ):
        first_case = student_cases[0]
        cases_by_student_payload.append(
            {
                'student_key': student_key,
                'display_name': first_case['display_name'],
                'display_email': first_case['display_email'],
                'legacy_user_id': first_case['legacy_user_id'],
                'match_status': first_case['match_status'],
                'case_count': len(student_cases),
                'cases': [serialize_case(case) for case in student_cases],
            }
        )

    payload = {
        'report_name': 'legacy_recoverableturns_blocked_report',
        'source_file': source_file,
        'summary': {
            key: value
            for key, value in summary.items()
            if key not in {'cases_by_student', 'cases_by_cause'}
        },
        'cases': [serialize_case(case) for case in cases],
        'cases_by_student': cases_by_student_payload,
        'cases_by_cause': {
            cause: [serialize_case(case) for case in cause_cases]
            for cause, cause_cases in sorted(summary['cases_by_cause'].items())
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_markdown(path: Path, *, json_path: Path, summary: dict) -> None:
    lines = [
        '# Legacy recoverable turns blocked report',
        '',
        f'- Source JSON: `{json_path.as_posix()}`',
        f'- Blocked rows for manual review: **{summary["blocked_case_count"]}**',
        f'- Affected student buckets: **{summary["student_count"]}**',
        f'- Current matched rows in blocked set: **{summary["matched_current_case_count"]}**',
        f'- Orphan rows: **{summary["orphan_case_count"]}**',
        f'- Students with multiple blocked rows: **{summary["students_with_multiple_cases"]}**',
        f'- Cases with secondary blockers hidden by importer order: **{summary["cases_with_secondary_blockers"]}**',
        '- Scope: report only, no business logic changes.',
        '',
        '## Breakdown by cause',
        '',
    ]

    for cause, count in summary['cause_counts'].items():
        lines.append(f'- `{cause}`: {count}')
    for blocker, count in summary['secondary_blocker_counts'].items():
        lines.append(f'- secondary `{blocker}`: {count}')
    lines.append('')

    for cause, signatures in summary['possible_sections_by_cause'].items():
        if not signatures:
            continue
        lines.append(f'### {cause}')
        lines.append('')
        for signature, count in signatures.items():
            lines.append(f'- `{signature}`: {count}')
        lines.append('')

    lines.extend(
        [
            '## Manual workflow',
            '',
            '1. Start with `legacy_recoverableturns_blocked_report.csv` to filter by `blocking_cause`, student, or legacy user id.',
            '2. Resolve `ambiguous_section` rows first using `possible_sections_label` plus the original day/hour.',
            '3. Review `orphan_user` rows against the legacy user export (`legacy_user_email` / `legacy_user_name`) before deciding whether to import or discard.',
            '4. Leave the single `inconsistent_state` row for explicit business confirmation before any backfill.',
            '',
            '## Cases grouped by student',
            '',
        ]
    )

    for _, student_cases in sorted(
        summary['cases_by_student'].items(),
        key=lambda item: (
            (item[1][0]['display_name'] or '').lower(),
            (item[1][0]['display_email'] or '').lower(),
            item[0],
        ),
    ):
        first_case = student_cases[0]
        heading_name = first_case['display_name'] or 'Name unavailable'
        heading_email = first_case['display_email'] or first_case['legacy_user_id']
        lines.append(f'### {heading_name} - `{heading_email}`')
        lines.append('')
        lines.append(f'- legacy user id: `{first_case["legacy_user_id"]}`')
        lines.append(f'- current match status: `{first_case["match_status"]}`')
        if first_case['current_user_email']:
            lines.append(f'- current app user: `{first_case["current_user_email"]}` / id `{first_case["current_user_id"]}`')
        if first_case['legacy_user_email'] and first_case['legacy_user_email'] != first_case['current_user_email']:
            lines.append(f'- legacy user export: `{first_case["legacy_user_email"]}`')
        lines.append(f'- blocked rows in this bucket: **{len(student_cases)}**')
        lines.append('')
        for case in student_cases:
            lines.append(
                f"- source `{case['source_index']}` / recoverable `{case['legacy_recoverableturn_id']}` / cause `{case['blocking_cause']}`"
            )
            lines.append(
                f"  original `{case['original_day']} {case['original_hour']}` -> assigned `{case['assigned_day'] or '-'} {case['assigned_hour'] or '-'}` / recovered `{str(case['recovered']).lower()}`"
            )
            lines.append(
                f"  cancelledWeek `{case['cancelled_week']}` / recoveryDate `{case['recovery_date'] or '-'}` / possible sections `{case['possible_sections_label'] or '-'}`"
            )
            if case['secondary_blockers']:
                lines.append(f"  secondary blockers: {', '.join(case['secondary_blockers'])}")
            lines.append(f"  detail: {case['blocking_detail']}")
            lines.append('')

    path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def main() -> int:
    args = parse_args()
    cases = build_cases(json_path=args.json_path, legacy_users_path=args.legacy_users_path)
    summary = summarize_cases(cases)

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)

    write_markdown(args.markdown_output, json_path=args.json_path, summary=summary)
    write_json(args.json_output, source_file=args.json_path.name, summary=summary, cases=cases)
    write_csv(args.csv_output, cases)

    print(
        json.dumps(
            {
                'blocked_case_count': summary['blocked_case_count'],
                'cause_counts': summary['cause_counts'],
                'markdown_report': args.markdown_output.as_posix(),
                'json_report': args.json_output.as_posix(),
                'csv_report': args.csv_output.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
