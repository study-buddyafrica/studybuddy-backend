from rest_framework import serializers
from apps.school.models import School

class SchoolSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = School
        fields = [
            "id", "name", "address", "city", "country",
            "contact", "created_by", "is_approved", "created_at"
        ]
        read_only_fields = ["id", "created_by", "is_approved", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        if user.is_superuser or user.is_staff:
            validated_data["is_approved"] = True
            
        elif hasattr(user, "teacher_profile") and user.teacher_profile.is_verified:
            validated_data["is_approved"] = False
        else:
            raise serializers.ValidationError(
                "Only admins or verified teachers can add a school."
            )

        validated_data["created_by"] = user
        return super().create(validated_data)
