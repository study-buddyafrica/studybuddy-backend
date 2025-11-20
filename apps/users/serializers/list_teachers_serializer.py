from rest_framework import serializers
from apps.users.models import TeacherProfile


class TeacherProfileListSerializer(serializers.ModelSerializer):
    """Optimized serializer for listing teachers"""
    full_name = serializers.SerializerMethodField()
    subjects = serializers.StringRelatedField(many=True)

    class Meta:
        model = TeacherProfile
        fields = [
            "id",
            "full_name",
            "bio",
            "hourly_rate",
            "subjects",
            "is_verified", 'profile_picture'
            'grade', 'experience'
        ]

    def get_full_name(self, obj):
        user = getattr(obj, "user", None)
        return f"{user.first_name} {user.last_name}".strip() if user else None
