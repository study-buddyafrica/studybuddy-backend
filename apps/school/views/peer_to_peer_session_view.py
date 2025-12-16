from rest_framework import viewsets
from django.db.models import Prefetch

from apps.school.models import LiveSession, CourseEnrollment
from apps.school.serializers.peer_to_peer_session_serializer import (
    PeerLiveSessionSerializer
)
from apps.core.permissions import IsPeerSessionManager


class PeerLiveSessionViewSet(viewsets.ModelViewSet):
    serializer_class = PeerLiveSessionSerializer
    permission_classes = [IsPeerSessionManager]

    def get_queryset(self):
        user = self.request.user
        qs = LiveSession.objects.select_related(
            "course__teacher__user", "teacher"
        ).prefetch_related(
            Prefetch(
                "course__enrollments",
                queryset=CourseEnrollment.objects.select_related("student__user"),
            )
        )

        if user.is_staff:
            return qs

        if hasattr(user, "teacher_profile"):
            return qs.filter(course__teacher=user.teacher_profile)

        if hasattr(user, "student_profile"):
            enrolled_course_ids = CourseEnrollment.objects.filter(
                student=user.student_profile, is_active=True
            ).values_list("course_id", flat=True)
            return qs.filter(course_id__in=enrolled_course_ids)

        return LiveSession.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
