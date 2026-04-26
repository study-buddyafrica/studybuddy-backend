from django.db import transaction
from rest_framework import serializers

from apps.core.models import User
from apps.core.auth.serializers.email_verification_serializer import (
    EmailVerificationCode,
)
from apps.school.models import EducationLevel
from apps.users.models import TeacherProfile, StudentProfile, ParentProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=True)
    education_level_id = serializers.UUIDField(
        required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "username",
            "password",
            "confirm_password",
            "role",
            "country",
            "education_level_id",
        ]
        read_only_fields = ["id"]

    def validate_education_level_id(self, value):
        if value is None:
            return value
        if not EducationLevel.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid education level id.")
        return value

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        # =====================================================================
        # BYPASS: Temporarily disabling email verification check
        # TODO: Uncomment this block once AWS App Passwords are configured
        # =====================================================================
        # verified = EmailVerificationCode.objects.filter(
        #     email=email,
        #     user__isnull=True
        # ).filter(verified_at__isnull=False).exists()
        # if not verified:
        #     raise serializers.ValidationError(
        #         "Please verify your email before " \
        #         "completing registration."
        #     )
        # =====================================================================

        return email

    def validate(self, data):
        """General validation for user registration."""
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if len(data.get("first_name", "")) < 2:
            raise serializers.ValidationError(
                {"first_name": "First name must be at least 2 characters."}
            )
        if len(data.get("last_name", "")) < 2:
            raise serializers.ValidationError(
                {"last_name": "Last name must be at least 2 characters."}
            )

        if data.get("role") == "student" and data.get("education_level_id") is None:
            # Keep backward compatibility for older clients by defaulting to K-12.
            k12_level = EducationLevel.objects.filter(
                code=EducationLevel.AudienceTier.K12
            ).first()
            data["education_level_id"] = k12_level.id if k12_level else None

        return data

    @transaction.atomic
    def create(self, validated_data):
        education_level_id = validated_data.pop("education_level_id", None)
        validated_data.pop("confirm_password", None)
        email = validated_data["email"].lower().strip()
        user = User.objects.create_user(**validated_data)
        user.account_confirmed = True
        user.save(update_fields=["account_confirmed"])
        EmailVerificationCode.objects.filter(email=email, user__isnull=True).delete()

        role = user.role
        if role == "teacher":
            TeacherProfile.objects.create(user=user, hourly_rate=0.00)
        elif role == "student":
            education_level = None
            if education_level_id:
                education_level = EducationLevel.objects.filter(
                    id=education_level_id
                ).first()
            StudentProfile.objects.create(user=user, education_level=education_level)
        elif role == "parent":
            ParentProfile.objects.create(user=user)

        return user

    def to_representation(self, instance):
        """Response after successful registration."""
        return {
            "message": "User registered successfully.",
            "user": {
                "id": instance.id,
                "email": instance.email,
                "username": instance.username,
                "first_name": instance.first_name,
                "last_name": instance.last_name,
                "role": instance.role,
            },
        }
