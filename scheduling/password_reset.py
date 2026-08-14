import hashlib
import hmac
import logging
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.contrib.sessions.models import Session
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.utils import timezone

from .models import PasswordResetRateLimit


logger = logging.getLogger(__name__)


def normalize_reset_email(value):
    return unicodedata.normalize('NFKC', value or '').strip().casefold()


def principal_digest(value):
    return hmac.new(
        settings.PASSWORD_RESET_RATE_LIMIT_SECRET.encode('utf-8'),
        value.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def consume_limit(*, scope, digest, limit, now=None):
    """Consume a shared one-hour allowance using a row lock on the SQL database."""
    now = now or timezone.now()
    with transaction.atomic():
        try:
            counter = PasswordResetRateLimit.objects.select_for_update().get(
                scope=scope,
                principal_digest=digest,
            )
        except PasswordResetRateLimit.DoesNotExist:
            try:
                with transaction.atomic():
                    PasswordResetRateLimit.objects.create(
                        scope=scope,
                        principal_digest=digest,
                        window_started_at=now,
                        count=0,
                    )
            except IntegrityError:
                pass
            counter = PasswordResetRateLimit.objects.select_for_update().get(
                scope=scope,
                principal_digest=digest,
            )

        if now - counter.window_started_at >= timedelta(hours=1):
            counter.window_started_at = now
            counter.count = 0
        allowed = counter.count < limit
        if allowed:
            counter.count += 1
        counter.save(update_fields=['window_started_at', 'count', 'updated_at'])
        return allowed


def allow_password_reset_request(*, email, ip_address):
    email_allowed = consume_limit(
        scope='email',
        digest=principal_digest(normalize_reset_email(email)),
        limit=settings.PASSWORD_RESET_EMAIL_LIMIT,
    )
    ip_allowed = consume_limit(
        scope='ip',
        digest=principal_digest(ip_address or ''),
        limit=settings.PASSWORD_RESET_IP_LIMIT,
    )
    return email_allowed and ip_allowed


def invalidate_user_sessions(user):
    """Remove every database-backed authenticated session for a reset user."""
    session_keys = []
    for session in Session.objects.all().only('session_key', 'session_data'):
        try:
            session_user_id = session.get_decoded().get('_auth_user_id')
        except Exception:  # Corrupt or obsolete sessions must not block a reset.
            continue
        if str(session_user_id) == str(user.pk):
            session_keys.append(session.session_key)
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()


class EunoiaPasswordResetView(PasswordResetView):
    form_class = PasswordResetForm
    template_name = 'scheduling/password_reset_form.html'
    email_template_name = 'scheduling/password_reset_email.txt'
    subject_template_name = 'scheduling/password_reset_subject.txt'
    from_email = settings.DEFAULT_FROM_EMAIL
    success_url = '/password-reset/done/'

    def form_valid(self, form):
        email = form.cleaned_data['email']
        ip_address = self.request.META.get('REMOTE_ADDR', '')
        allowed = allow_password_reset_request(email=email, ip_address=ip_address)
        if allowed:
            if getattr(settings, 'EUNOIA_E2E', False):
                domain_override = settings.E2E_PASSWORD_RESET_EMAIL_DOMAIN
                use_https = settings.E2E_PASSWORD_RESET_EMAIL_USE_HTTPS
            else:
                # Production always uses the validated canonical HTTPS origin.
                domain_override = settings.EUNOIA_PUBLIC_DOMAIN
                use_https = True
            try:
                form.save(
                    domain_override=domain_override,
                    use_https=use_https,
                    from_email=self.from_email,
                    email_template_name=self.email_template_name,
                    subject_template_name=self.subject_template_name,
                    request=self.request,
                )
            except Exception:
                # Keep the HTTP response neutral and never log the email, token, or password.
                logger.error('Password reset email delivery failed.')
        logger.info('Password reset requested; rate_limit=%s.', 'allowed' if allowed else 'blocked')
        return HttpResponseRedirect(self.get_success_url())


class EunoiaPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = SetPasswordForm
    template_name = 'scheduling/password_reset_confirm.html'
    success_url = '/password-reset/complete/'

    def form_valid(self, form):
        response = super().form_valid(form)
        invalidate_user_sessions(self.user)
        logger.info('Password reset completed.')
        return response
