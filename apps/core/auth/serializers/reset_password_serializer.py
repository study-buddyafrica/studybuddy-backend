import random
from rest_framework import serializers
from apps.core.models import User

from apps.core.models import ResetPasswordCode
from apps.core.utils.send_reset_password_code import send_password_reset_code


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()

    def save(self):
        email = self.validated_data["email"]
        if not User.objects.filter(email=email).exists():
            return True

        code = f"{random.randint(100000, 999999)}"
        ResetPasswordCode.objects.filter(email=email).delete()
        ResetPasswordCode.objects.create(email=email, code=code)
        send_password_reset_code(email, code)
        return True


def _get_valid_reset_record(email: str, code: str) -> ResetPasswordCode:
    try:
        record = ResetPasswordCode.objects.get(email=email, code=code, verified=False)
    except ResetPasswordCode.DoesNotExist as exc:
        raise serializers.ValidationError({"code": "Invalid or expired code."}) from exc

    if record.is_expired():
        record.delete()
        raise serializers.ValidationError({"code": "This reset code has expired."})

    return record


class VerifyPasswordResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

    def validate_email(self, value):
        return value.lower().strip()

    def save(self):
        email = self.validated_data["email"]
        code = self.validated_data["code"]
        _get_valid_reset_record(email=email, code=code)
        return True


class ConfirmPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def validate_email(self, value):
        return value.lower().strip()

    def save(self):
        email = self.validated_data["email"]
        code = self.validated_data["code"]

        record = _get_valid_reset_record(email=email, code=code)

        record.verified = True
        record.save(update_fields=["verified"])
        user = User.objects.get(email=email)
        user.set_password(self.validated_data["new_password"])
        user.save()

        return user
