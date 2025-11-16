from rest_framework import serializers
from django.utils import timezone
from django.core.cache import cache

from apps.core.utils.email_verification import send_verification_email
from apps.core.models import EmailVerificationCode, User

class PreRegisterEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def save(self):
        email = self.validated_data["email"]

        EmailVerificationCode.objects.filter(email=email, user__isnull=True).delete()

        code = EmailVerificationCode.generate_code()

        EmailVerificationCode.objects.create(email=email, code=code)

        send_verification_email(email, code)

        return {"message": "Verification code sent."}


class PreRegistrationVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs["email"]
        code = attrs["code"]

        try:
            record = EmailVerificationCode.objects.filter(
                email=email, code=code, user__isnull=True
            ).latest("created_at")
        except EmailVerificationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired code.")

        if record.is_expired():
            record.delete()
            raise serializers.ValidationError("Code expired.")

        attrs["record"] = record
        return attrs

    def save(self):
        record = self.validated_data["record"]

        cache.set(f"verified_email:{record.email}", True, timeout=600)

        return {"message": "Email verified successfully."}
