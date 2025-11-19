from django.db import transaction
from rest_framework import serializers

from apps.core.models import User
from apps.core.auth.serializers.email_verification_serializer import EmailVerificationCode
from apps.users.models import TeacherProfile, StudentProfile, ParentProfile

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", 
            "last_name", "username", "password", 
            "confirm_password", "role",
            "country"
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        verified = EmailVerificationCode.objects.filter(
            email=email, 
            user__isnull=True
        ).filter(verified_at__isnull=False).exists()
        if not verified:
            raise serializers.ValidationError(
                "Please verify your email before " \
                "completing registration."
            )
        
        return email

    def validate(self, data):
        """General validation for user registration."""
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if len(data.get("first_name", "")) < 2:
            raise serializers.ValidationError({"first_name": "First name must be at least 2 characters."})
        if len(data.get("last_name", "")) < 2:
            raise serializers.ValidationError({"last_name": "Last name must be at least 2 characters."})
        return data

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        email = validated_data["email"].lower().strip()
        user = User.objects.create_user(**validated_data)
        user.account_confirmed = True
        user.save(update_fields=["account_confirmed"])
        EmailVerificationCode.objects.filter(
            email=email, 
            user__isnull=True
        ).update(user=user)

        role = user.role
        if role == "teacher":
            TeacherProfile.objects.create(user=user)
        elif role == "student":
            StudentProfile.objects.create(user=user)
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
