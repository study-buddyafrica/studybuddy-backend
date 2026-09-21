from django.core.mail import EmailMultiAlternatives, get_connection
from django.conf import settings
from django.template.loader import render_to_string
import logging
import requests

logger = logging.getLogger(__name__)


def _send_via_resend(api_key: str, to_email: str, subject: str, text_body: str, html_body: str, from_email: str) -> bool:
    """Send transactional email via Resend HTTP API (Port 443 HTTPS)."""
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": from_email,
        "to": [to_email] if isinstance(to_email, str) else to_email,
        "subject": subject,
        "text": text_body or "",
    }
    if html_body:
        payload["html"] = html_body

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return True


def _send_via_brevo(api_key: str, to_email: str, subject: str, text_body: str, html_body: str, from_email: str) -> bool:
    """Send transactional email via Brevo HTTP API (Port 443 HTTPS)."""
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    sender_name = "StudyBuddy"
    sender_email = from_email
    if "<" in from_email and ">" in from_email:
        sender_name = from_email.split("<")[0].strip()
        sender_email = from_email.split("<")[1].split(">")[0].strip()

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}] if isinstance(to_email, str) else [{"email": e} for e in to_email],
        "subject": subject,
        "textContent": text_body or "",
    }
    if html_body:
        payload["htmlContent"] = html_body

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return True


def send_email(
    to_email, 
    subject, 
    text_body=None, 
    html_body=None, 
    context=None, 
    template_name=None, 
    fail_silently=False,
):
    """
    Send email using HTTP API (Resend/Brevo) if configured, or Django's EmailMultiAlternatives (SMTP).
    Supports plain text, HTML, and template-based rendering.
    Returns True if email was sent successfully, False if fail_silently=True and sending failed.
    """

    if not to_email:
        raise ValueError("Recipient email (to_email) is required.")

    if not text_body and not html_body and not template_name:
        raise ValueError("Email content (text, html, or template) must be provided.")

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@studybuddy.africa"
    host_user = getattr(settings, "EMAIL_HOST_USER", None)
    if "@" not in str(from_email) and host_user:
        from_email = f"{from_email} <{host_user}>"

    if template_name and context:
        html_body = render_to_string(template_name, context)
        if not text_body:
            text_body = render_to_string(template_name, context)

    # 1. Check for Resend HTTP API (Port 443 - works on Render Free tier)
    resend_api_key = getattr(settings, "RESEND_API_KEY", None)
    if resend_api_key:
        try:
            _send_via_resend(resend_api_key, to_email, subject, text_body, html_body, from_email)
            logger.info(f"Email sent successfully via Resend to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Resend to {to_email}: {e}", exc_info=True)
            if fail_silently:
                return False
            raise

    # 2. Check for Brevo HTTP API (Port 443 - works on Render Free tier)
    brevo_api_key = getattr(settings, "BREVO_API_KEY", None)
    if brevo_api_key:
        try:
            _send_via_brevo(brevo_api_key, to_email, subject, text_body, html_body, from_email)
            logger.info(f"Email sent successfully via Brevo to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Brevo to {to_email}: {e}", exc_info=True)
            if fail_silently:
                return False
            raise

    # 3. Fallback to standard Django email backend (SMTP / Console) with explicit timeout
    timeout = getattr(settings, "EMAIL_TIMEOUT", 5)
    try:
        connection = get_connection(
            backend=getattr(settings, "EMAIL_BACKEND", None),
            host=getattr(settings, "EMAIL_HOST", "smtp.gmail.com"),
            port=getattr(settings, "EMAIL_PORT", 587),
            username=getattr(settings, "EMAIL_HOST_USER", None),
            password=getattr(settings, "EMAIL_HOST_PASSWORD", None),
            use_tls=getattr(settings, "EMAIL_USE_TLS", True),
            use_ssl=getattr(settings, "EMAIL_USE_SSL", False),
            fail_silently=fail_silently,
            timeout=timeout,
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body or "",
            from_email=from_email,
            to=[to_email] if isinstance(to_email, str) else to_email,
            connection=connection,
        )

        if html_body:
            msg.attach_alternative(html_body, "text/html")

        msg.send()
        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(
            f"Failed to send email via backend to {to_email}: {e}. "
            f"Note: Render Free tier blocks outbound SMTP ports 25/465/587. "
            f"Configure RESEND_API_KEY or BREVO_API_KEY to send emails via HTTP on Render.",
            exc_info=True,
        )
        if fail_silently:
            return False
        raise