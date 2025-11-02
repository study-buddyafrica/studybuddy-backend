from rest_framework import serializers
from apps.core.models import User

class UserUpdateSerializer(serializers.ModelSerializer):
    """For updating user details safely"""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "birth_date", "profile_picture", "role"]
        read_only_fields = ["role"]

    def update(self, instance, validated_data):
        """Update user profile"""
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance