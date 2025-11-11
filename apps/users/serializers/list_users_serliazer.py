from rest_framework import serializers
from apps.core.models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer for viewing user info (safe fields only)."""

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name",
            "username", "role", "is_active", "is_staff", "is_verified"
        ]
        read_only_fields = fields