import os
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from config import settings as app_settings
from apps.core.models import EmailVerificationCode, User
from apps.school.models import EducationLevel


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
        "EMAIL_HOST_USER": "",
        "EMAIL_HOST_PASSWORD": "",
        "MAIL_USERNAME": "legacy@example.com",
        "MAIL_PASSWORD": "legacy-app-password",
    }, clear=False)
    def test_uses_legacy_mail_credentials_when_email_credentials_missing(self):
        self.assertEqual(
            app_settings._env_first_stripped("EMAIL_HOST_USER", "MAIL_USERNAME"), 
            "legacy@example.com"
        )
        self.assertEqual(
            app_settings._env_first_stripped("EMAIL_HOST_PASSWORD", "MAIL_PASSWORD"),
            "legacy-app-password"
        )

    @patch.dict(os.environ, {
        "DEBUG": "true",
        "MAIL_DEBUG_CONSOLE": "true",
        "EMAIL_HOST_USER": "",
        "EMAIL_HOST_PASSWORD": "",
        "MAIL_USERNAME": "",
        "MAIL_PASSWORD": "",
    }, clear=False)
    def test_uses_console_backend_when_smtp_credentials_are_missing(self):
        self.assertEqual(
            app_settings.get_email_backend(),
            "django.core.mail.backends.console.EmailBackend",
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_email_settings_helpers_have_safe_defaults(self):
        self.assertEqual(
            app_settings._env_first("EMAIL_PORT", "MAIL_PORT", default="587"),
            "587",
        )
        self.assertIsNone(
            app_settings._env_first_stripped("EMAIL_HOST_USER", "MAIL_USERNAME")
        )
        self.assertTrue(
            app_settings._env_bool("EMAIL_USE_TLS", "MAIL_USE_TLS", default="true")
        )


class EmailVerificationSignalTests(TestCase):
    @patch("apps.core.signals.send_verification_email.send_verification_email_to_address")
    def test_verification_email_dispatch_waits_until_transaction_commit(self, send_email):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            EmailVerificationCode.objects.create(
                email="learner@example.com",
                code="123456",
            )

        send_email.assert_not_called()
        self.assertEqual(len(callbacks), 1)

        callbacks[0]()

        send_email.assert_called_once_with("learner@example.com", "123456")

    @patch("apps.core.signals.send_verification_email.send_verification_email_to_address")
    def test_verification_email_is_not_sent_when_code_update_saves(self, send_email):
        code = EmailVerificationCode.objects.create(
            email="learner@example.com",
            code="123456",
        )
        send_email.reset_mock()

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            code.code = "654321"
            code.save(update_fields=["code"])

        self.assertEqual(callbacks, [])
        send_email.assert_not_called()


class AuthRegressionTests(APITestCase):
    def setUp(self):
        self.k12, _ = EducationLevel.objects.update_or_create(
            code=EducationLevel.AudienceTier.K12,
            defaults={
                "name": "K-12",
                "description": "Primary and secondary education tracks.",
            },
        )

    @patch(
        "apps.core.signals.send_verification_email.send_verification_email_to_address",
        return_value=True,
    )
    def test_registration_sequence_and_refresh_rotation_blacklists_old_token(self, send_email):
        email = "learner@example.com"

        with self.captureOnCommitCallbacks(execute=True):
            request_response = self.client.post(
                "/api/verify-email/request/",
                {"email": email},
                format="json",
            )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        send_email.assert_called_once()

        code = EmailVerificationCode.objects.get(email=email)
        confirm_response = self.client.post(
            "/api/verify-email/confirm/",
            {"email": email, "code": code.code},
            format="json",
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        register_response = self.client.post(
            "/api/users/register/",
            {
                "email": email,
                "first_name": "Jane",
                "last_name": "Learner",
                "username": "jane-learner",
                "password": "StrongPass123",
                "confirm_password": "StrongPass123",
                "role": "student",
                "country": "Kenya",
                "education_level_id": str(self.k12.id),
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.get(email=email).account_confirmed)

        login_response = self.client.post(
            "/api/login/",
            {"email": email, "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        refresh_token = login_response.data["refresh"]

        refresh_response = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", refresh_response.data)

        reused_response = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(reused_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(
        "apps.core.signals.send_verification_email.send_verification_email_to_address",
        return_value=True,
    )
    def test_expose_verification_code_when_setting_enabled(self, send_email):
        with self.settings(EXPOSE_VERIFICATION_CODE=True):
            response = self.client.post(
                "/api/verify-email/request/",
                {"email": "code-exposed@example.com"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("code", response.data)
            self.assertEqual(len(response.data["code"]), 6)


class SendEmailHttpApiTests(SimpleTestCase):
    def test_sanitize_from_email_valid_rfc5322(self):
        from apps.core.utils.send_email import sanitize_from_email
        result = sanitize_from_email("StudyBuddy Africa <noreply@studybuddy.africa>")
        self.assertEqual(result, "StudyBuddy Africa <noreply@studybuddy.africa>")

    def test_sanitize_from_email_strips_outer_quotes(self):
        from apps.core.utils.send_email import sanitize_from_email
        result_double = sanitize_from_email('"StudyBuddy Africa <noreply@studybuddy.africa>"')
        result_single = sanitize_from_email("'StudyBuddy Africa <noreply@studybuddy.africa>'")
        self.assertEqual(result_double, "StudyBuddy Africa <noreply@studybuddy.africa>")
        self.assertEqual(result_single, "StudyBuddy Africa <noreply@studybuddy.africa>")

    def test_sanitize_from_email_strips_quotes_from_display_name(self):
        from apps.core.utils.send_email import sanitize_from_email
        result = sanitize_from_email('"StudyBuddy Africa" <noreply@studybuddy.africa>')
        self.assertEqual(result, "StudyBuddy Africa <noreply@studybuddy.africa>")

    def test_sanitize_from_email_fallbacks(self):
        from apps.core.utils.send_email import sanitize_from_email, DEFAULT_FROM_EMAIL_SAFE
        # Bare name string (cause of Resend 422 in testing sync)
        self.assertEqual(sanitize_from_email("Studybuddy Africa"), DEFAULT_FROM_EMAIL_SAFE)
        # Bare unbracketed email address
        self.assertEqual(sanitize_from_email("noreply@studybuddy.africa"), DEFAULT_FROM_EMAIL_SAFE)
        # Unverified domain
        self.assertEqual(sanitize_from_email("StudyBuddy <admin@gmail.com>"), DEFAULT_FROM_EMAIL_SAFE)
        # None and empty string
        self.assertEqual(sanitize_from_email(None), DEFAULT_FROM_EMAIL_SAFE)
        self.assertEqual(sanitize_from_email(""), DEFAULT_FROM_EMAIL_SAFE)

    def test_sanitize_from_email_preserves_other_studybuddy_senders(self):
        from apps.core.utils.send_email import sanitize_from_email
        result = sanitize_from_email("StudyBuddy Support <support@studybuddy.africa>")
        self.assertEqual(result, "StudyBuddy Support <support@studybuddy.africa>")

    @patch("apps.core.utils.send_email.requests.post")
    def test_send_email_via_resend(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status.return_value = None

        with self.settings(RESEND_API_KEY="re_test_12345", DEFAULT_FROM_EMAIL='"StudyBuddy Africa <noreply@studybuddy.africa>"'):
            from apps.core.utils.send_email import send_email
            result = send_email(
                to_email="test@example.com",
                subject="Test Resend",
                text_body="Hello Resend",
            )
            self.assertTrue(result)
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "https://api.resend.com/emails")
            self.assertIn("Bearer re_test_12345", kwargs["headers"]["Authorization"])
            self.assertEqual(kwargs["json"]["from"], "StudyBuddy Africa <noreply@studybuddy.africa>")

    @patch("apps.core.utils.send_email.requests.post")
    def test_send_email_via_resend_with_bare_name_setting_falls_back(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status.return_value = None

        with self.settings(RESEND_API_KEY="re_test_12345", DEFAULT_FROM_EMAIL="Studybuddy Africa"):
            from apps.core.utils.send_email import send_email
            result = send_email(
                to_email="test@example.com",
                subject="Test Bare Name Fallback",
                text_body="Hello Resend",
            )
            self.assertTrue(result)
            mock_post.assert_called_once()
            _, kwargs = mock_post.call_args
            self.assertEqual(kwargs["json"]["from"], "StudyBuddy Africa <noreply@studybuddy.africa>")

    @patch("apps.core.utils.send_email.requests.post")
    def test_send_email_via_brevo(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status.return_value = None

        with self.settings(RESEND_API_KEY=None, BREVO_API_KEY="xkeysib-test-12345"):
            from apps.core.utils.send_email import send_email
            result = send_email(
                to_email="test@example.com",
                subject="Test Brevo",
                text_body="Hello Brevo",
            )
            self.assertTrue(result)
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "https://api.brevo.com/v3/smtp/email")
            self.assertEqual(kwargs["headers"]["api-key"], "xkeysib-test-12345")
