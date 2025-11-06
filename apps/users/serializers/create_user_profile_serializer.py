from django.db import transaction
from rest_framework import serializers
from apps.core.utils.redis_client import r
from apps.core.models import User
from apps.users.models import TeacherProfile, StudentProfile, ParentProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", 
             "username", "password", "confirm_password", "role",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        """Ensure email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

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
        """
        Create a user and their associated profile automatically.
        Rate limit requests using Redis.
        """
        email = validated_data["email"]
        rate_limit_key = f"user_create_rate_limit:{email}"

        # Check Redis rate limit
        if r.exists(rate_limit_key):
            raise serializers.ValidationError(
                "Please wait 60 seconds before trying to register again."
            )

        validated_data.pop("confirm_password", None)

        # Create user
        user = User.objects.create_user(**validated_data)

        # Create related profile based on role
        role = user.role
        if role == "teacher":
            TeacherProfile.objects.create(user=user)
        elif role == "student":
            StudentProfile.objects.create(user=user)
        elif role == "parent":
            ParentProfile.objects.create(user=user)

        # Set rate limit flag
        r.setex(rate_limit_key, 60, "1")

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
