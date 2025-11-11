from rest_framework import serializers
from django.utils import timezone
from apps.core.models import EmailVerificationCode, User

class EmailVerificationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        code = attrs.get("code")

        if user.account_confirmed:
            raise serializers.ValidationError("Your email is already verified.")

        try:
            verification = EmailVerificationCode.objects.filter(
                user=user, code=code
            ).latest("created_at")
        except EmailVerificationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification code.")

        if verification.is_expired():
            verification.delete()
            raise serializers.ValidationError("Verification code has expired. Please request a new one.")

        attrs["verification"] = verification
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        verification = self.validated_data["verification"]
        user.account_confirmed = True
        user.save(update_fields=["account_confirmed"])
        verification.delete()
        EmailVerificationCode.objects.filter(user=user).delete()

        return {"message": "Email verified successfully."}
