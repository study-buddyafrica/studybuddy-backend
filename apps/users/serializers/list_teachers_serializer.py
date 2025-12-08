from rest_framework import serializers
from apps.users.models import TeacherProfile


class TeacherProfileListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    school = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = [
            "id",
            "full_name",
            "bio",
            "hourly_rate",
            "subjects",
            "is_verified",
            "profile_picture",
            "grade",
            "experience",
            "school",
        ]

    def get_full_name(self, obj):
        user = getattr(obj, "user", None)
        if not user:
            return None
        return f"{user.first_name} {user.last_name}".strip()

    def get_subjects(self, obj):
        subjects = obj.subjects.all()

        if not subjects.exists():
            return []

        return [{"id": s.id, "name": s.name} for s in subjects]

    def get_grade(self, obj):
        grades = obj.grade.all()
        return [g.level for g in grades] if grades.exists() else []

    def get_school(self, obj):
        school = getattr(obj, "school", None)
        if not school:
            return None

        return {
            "id": school.id,
            "name": school.name,
            "city": school.city,
            "country": school.country,
            "address": school.address,
        }
