from rest_framework import serializers

from apps.school.models import CourseEnrollment
from apps.users.models import StudentLead


class StudentLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentLead
        fields = ["id", "course", "student_profile", "is_a_lead"]
        read_only_fields = ["id"]

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
