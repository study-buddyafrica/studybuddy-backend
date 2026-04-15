from rest_framework import generics, permissions
from apps.school.models import LiveSession
from apps.school.serializers.livesession_serializer import LiveSessionSerializer
from apps.core.permissions import IsTeacherOrAdmin, IsVerified


class TeacherLiveLessonsView(generics.ListAPIView):
    """
    Teachers can view all their live lessons/sessions.
    
    Endpoint: /api/teacher/live-lessons/
    """
    serializer_class = LiveSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified, IsTeacherOrAdmin]

    def get_queryset(self):
        """Return only live lessons taught by the authenticated teacher"""
        user = self.request.user
        
        # Admin sees all live sessions
        if user.is_staff or user.is_superuser:
            return LiveSession.objects.select_related(
                "teacher__user",
                "session__student__user"
            ).order_by("-started_at")

        # Teachers see only their own live sessions
        if hasattr(user, "teacher_profile"):
            return LiveSession.objects.select_related(
                "teacher__user",
                "session__student__user"
            ).filter(
                teacher=user.teacher_profile
            ).order_by("-started_at")

        return LiveSession.objects.none()
