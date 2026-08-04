"""Export a read-only CSV audit of expected fixed-plan bookings.

Usage:
    python scripts/audit_expected_fixed_bookings.py --start-date 2026-08-01 --end-date 2026-08-31

The script only executes SELECT queries through Django's ORM. It does not call
reconcilers or any create, update, or delete operation. CSV is written to
stdout; argument and runtime errors are written to stderr.
"""

import argparse
import csv
import os
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from scheduling.fixed_booking_audit import CSV_COLUMNS, audit_expected_fixed_bookings  # noqa: E402


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use YYYY-MM-DD.') from exc


def parse_args():
    parser = argparse.ArgumentParser(description='Read-only audit of expected fixed-plan bookings.')
    parser.add_argument('--start-date', required=True, type=parse_date)
    parser.add_argument('--end-date', required=True, type=parse_date)
    args = parser.parse_args()
    if args.start_date > args.end_date:
        parser.error('--start-date must be on or before --end-date.')
    return args


def main():
    args = parse_args()
    writer = csv.DictWriter(sys.stdout, fieldnames=CSV_COLUMNS, extrasaction='raise')
    writer.writeheader()
    for row in audit_expected_fixed_bookings(start_date=args.start_date, end_date=args.end_date):
        writer.writerow(row)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'audit failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
