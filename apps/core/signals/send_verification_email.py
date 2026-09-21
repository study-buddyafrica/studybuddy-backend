from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from apps.core.models import EmailVerificationCode
from apps.core.utils.send_email_verification_code import send_verification_email_to_address

import logging
import threading
import sys

logger = logging.getLogger(__name__)


@receiver(post_save, sender=EmailVerificationCode, dispatch_uid="send_verification_email_on_code_created")
def send_verification_email_on_code_created(
    sender, instance, created, **kwargs
):
    """
    OTP email dispatch scheduled via post_save signal.
    Runs asynchronously in a background thread upon transaction commit
    so that network/SMTP latencies never block or crash user requests.
    """
    if not created:
        return

    if not instance.email:
        return

    # Skip if the email is already verified (e.g., admin-created or pre-verified)
    if instance.verified_at is not None:
        return

    email = instance.email
    code = instance.code
    code_id = instance.id

    # Log the verification code prominently in server logs for observability
    logger.info("OTP verification code generated for %s: %s (code id=%s)", email, code, code_id)

    def dispatch_email():
        def _send():
            try:
                sent = send_verification_email_to_address(email, code)
                if sent:
                    logger.info(
                        "Verification code email dispatched to %s (code id=%s)",
                        email,
                        code_id,
                    )
                else:
                    logger.warning(
                        "Verification code email dispatch failed (silent) to %s (code id=%s)",
                        email,
                        code_id,
                    )
            except Exception as exc:
                logger.error(
                    "Failed to send verification code email to %s: %s",
                    email,
                    exc,
                    exc_info=True,
                )
                # Do NOT re-raise — the code record exists; user can retry

        # In unit tests, run synchronously to satisfy mock assertions; in production, run async
        if getattr(settings, "TESTING", False) or "test" in sys.argv:
            _send()
        else:
            threading.Thread(target=_send, daemon=True).start()

    transaction.on_commit(dispatch_email)
