# apps/users/serializers.py
import json
from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.core.redis_client import r

User = get_user_model()


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

    def create(self, validated_data):
        """
        Create a user directly and apply Redis-based rate limiting.
        """
        email = validated_data["email"]
        rate_limit_key = f"user_create_rate_limit:{email}"

        # Prevent rapid re-submissions (60 seconds cooldown)
        if r.exists(rate_limit_key):
            raise serializers.ValidationError(
                "Please wait 60 seconds before trying to register again."
            )

        # Remove confirm_password from data
        validated_data.pop("confirm_password", None)

        # Create user
        user = User.objects.create_user(**validated_data)

        # Set rate limit (60 seconds)
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
