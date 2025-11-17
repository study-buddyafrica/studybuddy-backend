from rest_framework import serializers
from django.utils import timezone

from apps.core.utils.email_verification import send_verification_email_to_address   
from apps.core.models import EmailVerificationCode, User


class PreRegisterEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def save(self):
        email = self.validated_data["email"].lower().strip()
        EmailVerificationCode.objects.filter(email=email, user__isnull=True).delete()
        record = EmailVerificationCode.create_for_email(email=email, user=None)
        send_verification_email_to_address(email, record.code)
        return {"message": "Verification code sent."}


class VerifyPreRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        code = attrs["code"].strip()

        try:
            record = (
                EmailVerificationCode.objects
                .filter(email=email, user__isnull=True)
                .latest("created_at")
            )
        except EmailVerificationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification code.")

        if record.is_expired():
            record.delete()
            raise serializers.ValidationError("Verification code has expired.")

        if record.code != code:
            raise serializers.ValidationError("Invalid verification code.")

        attrs["record"] = record
        return attrs

    def save(self):
        record = self.validated_data["record"]
        record.verified_at = timezone.now()
        record.save(update_fields=["verified_at"])

        return {"message": "Email verified successfully."}
