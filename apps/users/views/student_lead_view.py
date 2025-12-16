from rest_framework import viewsets, permissions

from apps.users.models import StudentLead
from apps.users.serializers.student_lead_serializer import (
    StudentLeadSerializer
)
from apps.core.permissions import (
    IsTeacherAdminOrLeadStudent,
    IsVerified
)


class StudentLeadViewSet(viewsets.ModelViewSet):
    serializer_class = StudentLeadSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsVerified,
        IsTeacherAdminOrLeadStudent,
    ]

    def get_queryset(self):
        user = self.request.user

        qs = StudentLead.objects.select_related(
            "course__teacher__user", "student_profile__user"
        )

        if user.is_staff:
            return qs
        
        if hasattr(user, "teacher_profile"):
            return qs.filter(course__teacher=user.teacher_profile)

        if hasattr(user, "student_profile"):
            return qs.filter(student_profile=user.student_profile, is_a_lead=True)

        return StudentLead.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()
