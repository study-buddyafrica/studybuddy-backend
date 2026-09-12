"""Signal registrations for core app."""

from .sanitize_pre_save import sanitize_user_generated_text  # noqa: F401
from .send_verification_email import send_verification_email_on_code_created  # noqa: F401
