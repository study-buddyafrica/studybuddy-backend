from rest_framework import generics
from rest_framework import generics, permissions

from django.utils import timezone
from apps.core.permissions import IsVerified, IsTeacherOrAdmin
from apps.school.models import LiveSession
from apps.school.serializers.livesession_serializer import LiveSessionSerializer
from apps.school.serializers.course_lessions_serializer import (
    CourseLiveSessionCreateSerializer
)


class CourseLiveSessionCreateView(generics.CreateAPIView):
    serializer_class = CourseLiveSessionCreateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsTeacherOrAdmin,
        IsVerified,
    ]


class StudentCourseLiveSessionListView(generics.ListAPIView):
    serializer_class = LiveSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        student = self.request.user.student_profile

        return (
            LiveSession.objects.select_related("course", "teacher__user")
            .filter(
                course__enrollments__student=student,
                course__enrollments__is_active=True,
                ended_at__gte=timezone.now(),
            )
            .distinct()
            .order_by("started_at")
        )
