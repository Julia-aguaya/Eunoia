from __future__ import annotations

import argparse
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

from scheduling.legacy_userselections_import import (  # noqa: E402
    _extract_user_legacy_id,
    _infer_record_section_from_planned_selections,
    _resolve_section_for_planned_selection,
    _shift_month,
    build_confirmed_section_candidates_by_weekday_and_time,
    build_planned_monthly_selections,
    infer_cutoff_month,
    load_legacy_userselections,
)
from scheduling.models import Section, User, Weekday  # noqa: E402


DEFAULT_JSON_PATH = Path('eunoia.userselections.json')
DEFAULT_MARKDOWN_OUTPUT = Path('docs/reports/legacy-userselections-manual-resolution.md')
DEFAULT_JSON_OUTPUT = Path('docs/reports/legacy-userselections-manual-resolution.json')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate a manual-resolution report for unresolved legacy user selections.'
    )
    parser.add_argument('--json-path', type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument('--markdown-output', type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument('--json-output', type=Path, default=DEFAULT_JSON_OUTPUT)
    return parser.parse_args()


def serialize_case(case: dict) -> dict:
    return {
        'student': case['student'],
        'record_context': case['record_context'],
        'plan_context': case['plan_context'],
        'resolution': case['resolution'],
        'slot_candidates': case['slot_candidates'],
    }


def format_slot_label_es(parsed_slot) -> str:
    weekday_map = {
        Weekday.MONDAY: 'Lunes',
        Weekday.TUESDAY: 'Martes',
        Weekday.WEDNESDAY: 'Miercoles',
        Weekday.THURSDAY: 'Jueves',
        Weekday.FRIDAY: 'Viernes',
        Weekday.SATURDAY: 'Sabado',
        Weekday.SUNDAY: 'Domingo',
    }
    return f'{weekday_map.get(parsed_slot.weekday, parsed_slot.weekday)} {parsed_slot.start_time.strftime("%H:%M")}'


def render_markdown(*, cases_by_student: dict, summary: dict, json_path: Path) -> str:
    lines = [
        '# Legacy user selections pending manual resolution',
        '',
        f'- Source JSON: `{json_path.as_posix()}`',
        f'- Pending cases: **{summary["case_count"]}**',
        f'- Students affected: **{summary["student_count"]}**',
        f'- Cutoff month inferred from legacy data: `{summary["cutoff_month"]}`',
        '- Scope: unresolved cases only; no business logic or inferred sections added here.',
        '',
        '## Breakdown',
        '',
    ]

    for resolution_key, count in summary['resolution_breakdown'].items():
        lines.append(f'- `{resolution_key}`: {count}')
    for selection_kind, count in summary['selection_kind_breakdown'].items():
        lines.append(f'- `{selection_kind}`: {count}')
    lines.append(f'- Cases with current primary section set: {summary["cases_with_primary_section"]}')
    lines.append(f'- Cases with same-record inferred section available: {summary["cases_with_inferred_section"]}')
    lines.append(f'- Students with more than one pending case: {summary["students_with_multiple_cases"]}')
    lines.append('')

    for section_pair, count in summary['possible_section_breakdown'].items():
        lines.append(f'- `{section_pair}`: {count}')
    lines.append('')
    lines.append('## Cases by student')
    lines.append('')

    for student_key in sorted(cases_by_student):
        student_cases = cases_by_student[student_key]
        student = student_cases[0]['student']
        name = student['name'] or 'Name unavailable'
        lines.append(f'### {name} - `{student["email"]}`')
        lines.append('')
        lines.append(f'- Student id: `{student["id"]}`')
        lines.append(f'- Legacy user id: `{student["legacy_user_id"]}`')
        lines.append(f'- Current primary section: `{student["primary_section"] or "none"}`')
        lines.append(f'- Pending cases for this student: **{len(student_cases)}**')
        lines.append('')

        for index, case in enumerate(student_cases, start=1):
            record_context = case['record_context']
            plan_context = case['plan_context']
            resolution = case['resolution']
            slot_labels = ', '.join(slot['slot'] for slot in case['slot_candidates'])
            lines.append(f'#### Case {index} - {plan_context["effective_month"]} ({plan_context["selection_kind"]})')
            lines.append('')
            lines.append(f'- Legacy selection id: `{record_context["legacy_selection_id"]}`')
            lines.append(f'- Source entry index: `{record_context["source_index"]}`')
            lines.append(f'- Last change: `{record_context["last_change_at"] or "none"}`')
            lines.append(f'- Changes this month: `{record_context["changes_this_month"]}`')
            lines.append(f'- Legacy slots in this case: `{slot_labels}`')
            lines.append(f'- Resolution status: `{resolution["status"]}`')
            lines.append(f'- Possible sections to review manually: `{", ".join(resolution["possible_sections"])}`')
            if resolution['common_candidate_sections']:
                lines.append(
                    f'- Shared candidate sections across all slots: `{", ".join(resolution["common_candidate_sections"])}`'
                )
            if resolution['inferred_section']:
                lines.append(f'- Same-record inferred section: `{resolution["inferred_section"]}`')
            lines.append('')
            lines.append('| Legacy day/hour | Candidate sections |')
            lines.append('| --- | --- |')
            for slot in case['slot_candidates']:
                lines.append(f'| `{slot["slot"]}` | `{", ".join(slot["candidate_sections"] or ["missing mapping"] )}` |')
            lines.append('')

    return '\n'.join(lines).rstrip() + '\n'


def main() -> int:
    args = parse_args()
    records = load_legacy_userselections(args.json_path)
    cutoff_month = infer_cutoff_month(records)
    next_month = _shift_month(cutoff_month, 1)
    section_candidates_by_slot = build_confirmed_section_candidates_by_weekday_and_time()
    sections_by_code = {section.code: section for section in Section.objects.all()}
    users_by_legacy_id = {
        legacy_id: user
        for user in User.objects.filter(role='student').select_related('primary_section')
        for legacy_id in [_extract_user_legacy_id(user.notes)]
        if legacy_id
    }

    cases: list[dict] = []
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

        for planned_selection in planned_monthly_selections:
            resolution = _resolve_section_for_planned_selection(
                user=user,
                planned_selection=planned_selection,
                default_section=None,
                inferred_section=inferred_section,
                section_candidates_by_slot=section_candidates_by_slot,
                sections_by_code=sections_by_code,
            )
            if resolution.section is not None or resolution.status not in {'ambiguous', 'conflicting'}:
                continue

            slot_candidates = []
            candidate_sets = []
            for parsed_slot in planned_selection.slots:
                candidate_codes = list(
                    section_candidates_by_slot.get((parsed_slot.weekday, parsed_slot.start_time), ())
                )
                if candidate_codes:
                    candidate_sets.append(set(candidate_codes))
                slot_candidates.append(
                    {
                        'slot': format_slot_label_es(parsed_slot),
                        'candidate_sections': candidate_codes,
                    }
                )

            common_candidate_sections = sorted(set.intersection(*candidate_sets)) if candidate_sets else []
            possible_sections = sorted({code for slot in slot_candidates for code in slot['candidate_sections']})

            cases.append(
                {
                    'student': {
                        'id': user.id,
                        'email': user.email,
                        'name': user.get_full_name(),
                        'legacy_user_id': record.legacy_user_id,
                        'primary_section': user.primary_section.code if user.primary_section_id else None,
                    },
                    'record_context': {
                        'source_index': record.source_index,
                        'legacy_selection_id': record.legacy_selection_id,
                        'changes_this_month': record.changes_this_month,
                        'last_change_at': record.last_change_at.isoformat() if record.last_change_at else None,
                    },
                    'plan_context': {
                        'effective_month': planned_selection.month.isoformat(),
                        'selection_kind': planned_selection.selection_kind,
                    },
                    'resolution': {
                        'status': resolution.status,
                        'possible_sections': possible_sections,
                        'common_candidate_sections': common_candidate_sections,
                        'inferred_section': inferred_section.code if inferred_section else None,
                        'resolution_details': list(resolution.details),
                    },
                    'slot_candidates': slot_candidates,
                }
            )

    cases.sort(
        key=lambda case: (
            case['student']['name'].lower(),
            case['student']['email'].lower(),
            case['plan_context']['effective_month'],
            case['plan_context']['selection_kind'],
            case['record_context']['source_index'],
        )
    )

    cases_by_student: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        cases_by_student[case['student']['email']].append(case)

    resolution_breakdown = Counter(case['resolution']['status'] for case in cases)
    selection_kind_breakdown = Counter(case['plan_context']['selection_kind'] for case in cases)
    possible_section_breakdown = Counter(' + '.join(case['resolution']['possible_sections']) for case in cases)
    summary = {
        'case_count': len(cases),
        'student_count': len(cases_by_student),
        'cutoff_month': cutoff_month.isoformat(),
        'resolution_breakdown': dict(sorted(resolution_breakdown.items())),
        'selection_kind_breakdown': dict(sorted(selection_kind_breakdown.items())),
        'possible_section_breakdown': dict(sorted(possible_section_breakdown.items())),
        'cases_with_primary_section': sum(1 for case in cases if case['student']['primary_section']),
        'cases_with_inferred_section': sum(1 for case in cases if case['resolution']['inferred_section']),
        'students_with_multiple_cases': sum(1 for student_cases in cases_by_student.values() if len(student_cases) > 1),
    }

    markdown_output = args.markdown_output
    json_output = args.json_output
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)

    markdown_output.write_text(
        render_markdown(cases_by_student=cases_by_student, summary=summary, json_path=args.json_path),
        encoding='utf-8',
    )
    json_output.write_text(
        json.dumps(
            {
                'summary': summary,
                'cases': [serialize_case(case) for case in cases],
                'cases_by_student': {
                    student_key: [serialize_case(case) for case in student_cases]
                    for student_key, student_cases in sorted(cases_by_student.items())
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )

    print(f'Generated {len(cases)} unresolved cases into {markdown_output.as_posix()} and {json_output.as_posix()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
