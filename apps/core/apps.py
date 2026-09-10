from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'

    def ready(self):
        from .signals import sanitize_pre_save  # noqa: F401
        from .signals import send_verification_email_on_code_created  # noqa: F401
