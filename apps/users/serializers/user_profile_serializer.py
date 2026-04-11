"""User registration and profile serializers"""

from rest_framework import serializers
from apps.core.models import User
from apps.users.models import StudentProfile
from apps.core.validators import (
    validate_birth_date_student,
    validate_string_length,
)


class StudentRegistrationSerializer(serializers.Serializer):
    """
    Serializer for registering a student.
    Used by parents to register their children.
    """

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=201, required=False, allow_blank=True)
    username = serializers.CharField(max_length=30, required=True)
    password = serializers.CharField(
        min_length=8, max_length=128, write_only=True, required=True
    )
    confirm_password = serializers.CharField(
        min_length=8, max_length=128, write_only=True, required=False
    )
    birth_date = serializers.DateField(required=False, allow_null=True)

    def validate_first_name(self, value):
        """Validate first name"""
        validate_string_length(
            value, min_length=2, max_length=100, field_name="First name"
        )
        return value

    def validate_last_name(self, value):
        """Validate last name"""
        validate_string_length(
            value, min_length=2, max_length=100, field_name="Last name"
        )
        return value

    def validate_username(self, value):
        """Validate username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        """Validate email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_birth_date(self, value):
        """Validate student birth date"""
        if value:
            validate_birth_date_student(value)
        return value

    def validate(self, attrs):
        """Validate password confirmation and normalize name fields."""
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if confirm_password is not None and password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        first_name = (attrs.get("first_name") or "").strip()
        last_name = (attrs.get("last_name") or "").strip()
        full_name = (attrs.get("full_name") or "").strip()

        if (not first_name or not last_name) and full_name:
            parts = [part for part in full_name.split(" ") if part]
            if len(parts) == 1:
                first_name = parts[0]
                last_name = "Student"
            else:
                first_name = parts[0]
                last_name = " ".join(parts[1:])

        if not first_name or not last_name:
            raise serializers.ValidationError(
                "Provide first_name and last_name, or provide full_name."
            )

        validate_string_length(
            first_name, min_length=2, max_length=100, field_name="First name"
        )
        validate_string_length(
            last_name, min_length=2, max_length=100, field_name="Last name"
        )

        attrs["first_name"] = first_name
        attrs["last_name"] = last_name
        return attrs

    def create(self, validated_data):
        """Create student user"""
        user = User.objects.create_user(
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            username=validated_data["username"],
            password=validated_data["password"],
            role="student",
        )
        return user
