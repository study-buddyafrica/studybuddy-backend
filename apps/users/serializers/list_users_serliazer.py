from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.core.models import User


class UserSerializer(serializers.ModelSerializer):
    profile_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "username",
            "role",
            "is_active",
            "is_staff",
            "account_confirmed",
            "created_at",
            "last_login",
            "profile_id",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_id(self, obj) -> str | None:
        if hasattr(obj, "teacher_profile"):
            return str(obj.teacher_profile.id)
        if hasattr(obj, "parent_profile"):
            return str(obj.parent_profile.id)
        if hasattr(obj, "student_profile"):
            return str(obj.student_profile.id)
        return None
