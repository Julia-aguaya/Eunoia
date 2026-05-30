from dataclasses import dataclass

from django.utils import timezone

from ..audit import log_staff_recovery_credit_expired
from ..models import RecoveryCredit, RecoveryCreditStatus


@dataclass(frozen=True)
class ManualRecoveryExpiration:
    credit: RecoveryCredit
    changed: bool


@dataclass(frozen=True)
class RecoveryCreditBulkExpiration:
    expired_count: int
    skipped_count: int


def expire_recovery_credit(*, credit, actor=None, on_date=None, record_audit=False):
    changed = credit.expire_manually(on_date=on_date or timezone.localdate())
    if changed:
        credit.save(update_fields=['status', 'expires_at', 'updated_at'])
        if record_audit:
            log_staff_recovery_credit_expired(actor=actor, credit=credit, reason='manual')

    return ManualRecoveryExpiration(credit=credit, changed=changed)


def expire_overdue_recovery_credits(*, credits, actor=None, on_date=None, record_audit=False):
    reference_date = on_date or timezone.localdate()
    expired_count = 0
    skipped_count = 0

    for credit in credits:
        if credit.status != RecoveryCreditStatus.AVAILABLE:
            skipped_count += 1
            continue

        changed = credit.expire_if_needed(on_date=reference_date)
        if not changed:
            skipped_count += 1
            continue

        credit.save(update_fields=['status', 'updated_at'])
        if record_audit:
            log_staff_recovery_credit_expired(actor=actor, credit=credit, reason='overdue')
        expired_count += 1

    return RecoveryCreditBulkExpiration(expired_count=expired_count, skipped_count=skipped_count)
