from django.core.mail import EmailMultiAlternatives, get_connection
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

def send_email(to_email, subject, text_body=None, html_body=None, context=None, template_name=None):
    """
    Send email using Django's EmailMultiAlternatives.
    Supports plain text, HTML, and template-based rendering.
    """

    if not to_email:
        raise ValueError("Recipient email (to_email) is required.")

    if not text_body and not html_body and not template_name:
        raise ValueError("Email content (text, html, or template) must be provided.")

    if template_name and context:
        html_body = render_to_string(template_name, context)
        if not text_body:
            text_body = render_to_string(template_name, context)

    try:
        connection = get_connection(
            host=getattr(settings, "EMAIL_HOST", "smtp.gmail.com"),
            port=getattr(settings, "EMAIL_PORT", 587),
            username=getattr(settings, "EMAIL_HOST_USER", None),
            password=getattr(settings, "EMAIL_HOST_PASSWORD", None),
            use_tls=getattr(settings, "EMAIL_USE_TLS", True),
            fail_silently=False,
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body or "",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
            to=[to_email],
            connection=connection,
        )

        if html_body:
            msg.attach_alternative(html_body, "text/html")

        msg.send()
        logger.info(f"Email sent successfully to {to_email}")

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
        raise e
