import os
from unittest.mock import patch

from django.test import SimpleTestCase

from config import settings as app_settings


class EmailBackendConfigTests(SimpleTestCase):
    @patch.dict(os.environ, {
        "DEBUG": "true",
        "MAIL_DEBUG_CONSOLE": "true",
        "MAIL_USERNAME": "noreply@example.com",
        "MAIL_PASSWORD": "secret-app-password",
    }, clear=False)
    def test_uses_smtp_backend_when_smtp_credentials_exist(self):
        self.assertEqual(
            app_settings.get_email_backend(),
            "django.core.mail.backends.smtp.EmailBackend",
        )

    @patch.dict(os.environ, {
        "DEBUG": "true",
        "MAIL_DEBUG_CONSOLE": "true",
        "MAIL_USERNAME": "",
        "MAIL_PASSWORD": "",
    }, clear=False)
    def test_uses_console_backend_when_smtp_credentials_are_missing(self):
        self.assertEqual(
            app_settings.get_email_backend(),
            "django.core.mail.backends.console.EmailBackend",
        )
