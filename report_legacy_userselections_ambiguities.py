import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from scheduling.legacy_userselections_import import (  # noqa: E402
    build_confirmed_section_candidates_by_weekday_and_time,
    build_planned_monthly_selections,
    _extract_user_legacy_id,
    infer_cutoff_month,
    load_legacy_userselections,
    _format_slot_label,
    _infer_record_section_from_planned_selections,
    _resolve_section_for_planned_selection,
    _shift_month,
)
from scheduling.models import Section, User  # noqa: E402


ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / 'eunoia.userselections.json'
OUTPUT_DIR = ROOT / 'docs' / 'reports'
MARKDOWN_PATH = OUTPUT_DIR / 'legacy_userselections_ambiguous_sections_report.md'
JSON_REPORT_PATH = OUTPUT_DIR / 'legacy_userselections_ambiguous_sections_report.json'
CSV_REPORT_PATH = OUTPUT_DIR / 'legacy_userselections_ambiguous_sections_report.csv'


def _legacy_slot_pairs(raw_slots):
    pairs = []
    for raw_slot in raw_slots or []:
        if not isinstance(raw_slot, dict):
            continue
        day = str(raw_slot.get('day') or '').strip()
        hour = str(raw_slot.get('hour') or '').strip()
        if not day and not hour:
            continue
        pairs.append({'day': day, 'hour': hour})
    return pairs


def _legacy_slot_labels(raw_slots):
    labels = []
    for slot in _legacy_slot_pairs(raw_slots):
        day = slot['day'] or '?'
        hour = slot['hour'] or '?'
        labels.append(f'{day} {hour}'.strip())
    return labels


def _build_cases():
    raw_payload = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    raw_records_by_index = {index: record for index, record in enumerate(raw_payload, start=1)}
    records = load_legacy_userselections(JSON_PATH)
    cutoff_month = infer_cutoff_month(records)
    next_month = _shift_month(cutoff_month, 1)

    users_by_legacy_id = {
        legacy_id: user
        for user in User.objects.filter(role='student').select_related('primary_section')
        for legacy_id in [_extract_user_legacy_id(user.notes)]
        if legacy_id
    }
    sections_by_code = {section.code: section for section in Section.objects.all()}
    section_candidates_by_slot = build_confirmed_section_candidates_by_weekday_and_time()

    cases = []
    for record in records:
        user = users_by_legacy_id.get(record.legacy_user_id)
        if user is None:
            continue

        planned_monthly_selections = build_planned_monthly_selections(
            record,
            cutoff_month=cutoff_month,
            next_month=next_month,
        )
        if not planned_monthly_selections:
            continue

        inferred_section = _infer_record_section_from_planned_selections(
            planned_monthly_selections=planned_monthly_selections,
            section_candidates_by_slot=section_candidates_by_slot,
            sections_by_code=sections_by_code,
        )
        raw_record = raw_records_by_index[record.source_index]
        raw_original_selections = _legacy_slot_pairs(raw_record.get('originalSelections'))
        raw_temporary_selections = _legacy_slot_pairs(raw_record.get('temporarySelections'))
        raw_original_labels = _legacy_slot_labels(raw_record.get('originalSelections'))
        raw_temporary_labels = _legacy_slot_labels(raw_record.get('temporarySelections'))

        for planned_selection in planned_monthly_selections:
            resolution = _resolve_section_for_planned_selection(
                user=user,
                planned_selection=planned_selection,
                default_section=None,
                inferred_section=inferred_section,
                section_candidates_by_slot=section_candidates_by_slot,
                sections_by_code=sections_by_code,
            )
            if resolution.section is not None:
                continue

            planned_legacy_pairs = (
                raw_temporary_selections if planned_selection.selection_kind == 'temporary' else raw_original_selections
            )
            planned_legacy_labels = (
                raw_temporary_labels if planned_selection.selection_kind == 'temporary' else raw_original_labels
            )

            cases.append(
                {
                    'student_email': user.email,
                    'student_name': user.get_full_name(),
                    'student_id': user.id,
                    'legacy_user_id': record.legacy_user_id,
                    'legacy_userselection_id': record.legacy_selection_id,
                    'source_index': record.source_index,
                    'month': planned_selection.month.isoformat(),
                    'selection_kind': planned_selection.selection_kind,
                    'status': resolution.status,
                    'possible_sections': list(resolution.details),
                    'primary_section': user.primary_section.code if user.primary_section_id else '',
                    'inferred_section': inferred_section.code if inferred_section is not None else '',
                    'slot_labels': [_format_slot_label(slot) for slot in planned_selection.slots],
                    'planned_legacy_day_hour_pairs': planned_legacy_pairs,
                    'planned_legacy_labels': planned_legacy_labels,
                    'raw_original_selections': raw_original_selections,
                    'raw_temporary_selections': raw_temporary_selections,
                    'raw_original_labels': raw_original_labels,
                    'raw_temporary_labels': raw_temporary_labels,
                    'changes_this_month': record.changes_this_month,
                    'last_change_at': record.last_change_at.isoformat() if record.last_change_at else None,
                }
            )

    return cutoff_month, cases


def _write_json(cutoff_month, cases):
    grouped_counts = Counter(case['student_email'] for case in cases)
    status_counts = Counter(case['status'] for case in cases)
    conflict_counts = Counter(' | '.join(case['possible_sections']) for case in cases)
    grouped = defaultdict(list)
    for case in cases:
        grouped[case['student_email']].append(case)

    payload = {
        'report_name': 'legacy_userselections_ambiguous_sections_report',
        'source_file': str(JSON_PATH.name),
        'cutoff_month': cutoff_month.isoformat(),
        'case_count': len(cases),
        'student_count': len(grouped),
        'status_counts': dict(status_counts),
        'possible_section_conflicts': dict(conflict_counts),
        'students': [
            {
                'student_email': student_email,
                'student_name': grouped[student_email][0]['student_name'],
                'student_id': grouped[student_email][0]['student_id'],
                'legacy_user_id': grouped[student_email][0]['legacy_user_id'],
                'case_count': grouped_counts[student_email],
                'cases': sorted(
                    grouped[student_email],
                    key=lambda item: (
                        item['month'],
                        item['selection_kind'],
                        ', '.join(item['slot_labels']),
                        item['source_index'],
                    ),
                ),
            }
            for student_email in sorted(
                grouped,
                key=lambda email: (
                    grouped[email][0]['student_name'] or '',
                    email,
                ),
            )
        ],
    }
    JSON_REPORT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def _write_csv(cases):
    fieldnames = [
        'student_email',
        'student_name',
        'student_id',
        'legacy_user_id',
        'legacy_userselection_id',
        'source_index',
        'month',
        'selection_kind',
        'status',
        'possible_sections',
        'primary_section',
        'inferred_section',
        'legacy_day_hour',
        'slot_labels',
        'changes_this_month',
        'last_change_at',
        'raw_original_labels',
        'raw_temporary_labels',
    ]
    with CSV_REPORT_PATH.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case in sorted(
            cases,
            key=lambda item: (
                item['student_name'] or '',
                item['student_email'],
                item['month'],
                ', '.join(item['slot_labels']),
                item['source_index'],
            ),
        ):
            writer.writerow(
                {
                    'student_email': case['student_email'],
                    'student_name': case['student_name'],
                    'student_id': case['student_id'],
                    'legacy_user_id': case['legacy_user_id'],
                    'legacy_userselection_id': case['legacy_userselection_id'],
                    'source_index': case['source_index'],
                    'month': case['month'],
                    'selection_kind': case['selection_kind'],
                    'status': case['status'],
                    'possible_sections': ' | '.join(case['possible_sections']),
                    'primary_section': case['primary_section'],
                    'inferred_section': case['inferred_section'],
                    'legacy_day_hour': ' | '.join(
                        f"{slot['day']} {slot['hour']}" for slot in case['planned_legacy_day_hour_pairs']
                    ),
                    'slot_labels': ' | '.join(case['slot_labels']),
                    'changes_this_month': case['changes_this_month'],
                    'last_change_at': case['last_change_at'] or '',
                    'raw_original_labels': ' | '.join(case['raw_original_labels']),
                    'raw_temporary_labels': ' | '.join(case['raw_temporary_labels']),
                }
            )


def _write_markdown(cutoff_month, cases):
    grouped = defaultdict(list)
    for case in cases:
        grouped[case['student_email']].append(case)

    conflict_counts = Counter(' | '.join(case['possible_sections']) for case in cases)
    lines = [
        '# Legacy userselections ambiguous section report',
        '',
        f'- Source: `{JSON_PATH.name}`',
        f'- Cutoff month used by importer: `{cutoff_month.isoformat()}`',
        f'- Ambiguous unresolved plan specs: `{len(cases)}`',
        f'- Students affected: `{len(grouped)}`',
        '- Statuses: ' + ', '.join(
            f"`{status}`={count}" for status, count in sorted(Counter(case['status'] for case in cases).items())
        ),
        '- Conflict signatures: ' + ', '.join(
            f"`{signature}`={count}" for signature, count in sorted(conflict_counts.items())
        ),
        '',
        '## Manual workflow',
        '',
        '1. Take one student block at a time.',
        '2. Use the possible sections plus the legacy day/hour to confirm the real section in the business source.',
        '3. Mark the chosen section in your working sheet using the CSV or JSON export.',
        '4. After validation, use that curated mapping to backfill only the skipped plans.',
        '',
        '## Students',
        '',
    ]

    sorted_emails = sorted(
        grouped,
        key=lambda email: (
            grouped[email][0]['student_name'] or '',
            email,
        ),
    )
    for email in sorted_emails:
        student_cases = sorted(
            grouped[email],
            key=lambda item: (
                item['month'],
                item['selection_kind'],
                ', '.join(item['slot_labels']),
                item['source_index'],
            ),
        )
        first_case = student_cases[0]
        display_name = first_case['student_name'] or '(sin nombre)'
        lines.extend(
            [
                f"### {display_name} - `{email}`",
                '',
                f"- app user id: `{first_case['student_id']}`",
                f"- legacy user id: `{first_case['legacy_user_id']}`",
                f"- primary section actual: `{first_case['primary_section'] or 'none'}`",
                f"- unresolved cases: `{len(student_cases)}`",
                '',
            ]
        )
        for case in student_cases:
            legacy_day_hour = ', '.join(
                f"`{slot['day']} {slot['hour']}`" for slot in case['planned_legacy_day_hour_pairs']
            )
            possible_sections = ', '.join(f'`{section}`' for section in case['possible_sections']) or '`none`'
            lines.extend(
                [
                    f"- `{case['month']}` / `{case['selection_kind']}` / source entry `{case['source_index']}` / legacy selection `{case['legacy_userselection_id']}`",
                    f"  legacy day/hour: {legacy_day_hour}",
                    f"  normalized slots: {', '.join(f'`{slot}`' for slot in case['slot_labels'])}",
                    f"  possible sections: {possible_sections}",
                    f"  changesThisMonth: `{case['changes_this_month']}` / lastChange: `{case['last_change_at'] or 'null'}` / inferred section: `{case['inferred_section'] or 'none'}`",
                    f"  raw originalSelections: {', '.join(f'`{label}`' for label in case['raw_original_labels']) or '`empty`'}",
                    f"  raw temporarySelections: {', '.join(f'`{label}`' for label in case['raw_temporary_labels']) or '`empty`'}",
                    '',
                ]
            )

    MARKDOWN_PATH.write_text('\n'.join(lines), encoding='utf-8')


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cutoff_month, cases = _build_cases()
    _write_markdown(cutoff_month, cases)
    _write_json(cutoff_month, cases)
    _write_csv(cases)
    print(json.dumps({
        'case_count': len(cases),
        'markdown_report': str(MARKDOWN_PATH.relative_to(ROOT)),
        'json_report': str(JSON_REPORT_PATH.relative_to(ROOT)),
        'csv_report': str(CSV_REPORT_PATH.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
