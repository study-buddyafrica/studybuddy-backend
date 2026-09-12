from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import EmailVerificationCode
from apps.core.utils.send_email_verification_code import send_verification_email_to_address

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=EmailVerificationCode, dispatch_uid="send_verification_email_on_code_created")
def send_verification_email_on_code_created(
    sender, instance, created, **kwargs
):
    """
    OTP email dispatch scheduled via post_save signal.
    SMTP failures are caught and logged — they never abort the request
    that created the verification code.
    The email is sent after the database transaction is committed via
    transaction.on_commit() to avoid sending OTPs for rolled-back transactions.
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

    def dispatch_email():
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

    transaction.on_commit(dispatch_email)
