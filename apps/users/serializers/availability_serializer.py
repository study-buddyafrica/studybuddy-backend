from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.users.models import Availability


class AvailabilitySerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Availability
        fields = ["id", "teacher", "teacher_name", "date", "end_date", "is_blocked"]
        read_only_fields = ["id", "teacher", "teacher_name"]

    @extend_schema_field(serializers.CharField())
    def get_teacher_name(self, obj) -> str:
        """Return teacher full name"""
        if obj.teacher and obj.teacher.user:
            return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}"
        return ""

    def create(self, validated_data):
        """Automatically set teacher to the requesting user"""
        request = self.context.get("request")
        if not request or not hasattr(request.user, "teacher_profile"):
            raise serializers.ValidationError(
                "Only teachers can create availability slots."
            )

        validated_data["teacher"] = request.user.teacher_profile
        return super().create(validated_data)
