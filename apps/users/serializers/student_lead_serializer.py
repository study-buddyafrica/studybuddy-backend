from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.school.models import CourseEnrollment
from apps.users.models import StudentLead


class StudentLeadSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = StudentLead
        fields = [
            "id",
            "course",
            "course_title",
            "student_profile",
            "student_name",
            "is_a_lead",
        ]
        read_only_fields = ["id", "student_name", "course_title"]

    @extend_schema_field(serializers.CharField())
    def get_student_name(self, obj) -> str:
        """Return full student name for display"""
        if obj.student_profile and obj.student_profile.user:
            return f"{obj.student_profile.user.first_name} {obj.student_profile.user.last_name}"
        return str(obj.student_profile.id)

    @extend_schema_field(serializers.CharField())
    def get_course_title(self, obj) -> str:
        """Return course title for display"""
        return obj.course.title if obj.course else ""

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        course = attrs.get("course")
        student = attrs.get("student_profile")

        if not (user.is_staff or hasattr(user, "teacher_profile")):
            raise serializers.ValidationError(
                "Only teachers or admins can manage student leads."
            )

        if hasattr(user, "teacher_profile") and not user.is_staff:
            if course.teacher != user.teacher_profile:
                raise serializers.ValidationError(
                    "You can only assign leads for your own courses."
                )

        is_enrolled = CourseEnrollment.objects.filter(
            course=course, student=student, is_active=True
        ).exists()

        if not is_enrolled:
            raise serializers.ValidationError(
                "Student must be enrolled in the course to be a lead."
            )

        return attrs
