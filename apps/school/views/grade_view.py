from rest_framework import viewsets
from rest_framework import permissions

from apps.school.serializers.grade_serializer import GradeSerializer
from apps.school.models import Grade
from apps.core.permissions import IsTeacherOrAdmin, IsVerified
from apps.core.auth.views.pagination_view import StandardResultsSetPagination


class GradeViewSet(viewsets.ModelViewSet):
    serializer_class = GradeSerializer
    pagination_class = StandardResultsSetPagination
    queryset = Grade.objects.all().order_by("level")

    def get_permissions(self):
        """
        - List & Retrieve → Anyone
        - Create, Update, Delete → Only Teachers & Admin + Verified
        """
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        return [
            permissions.IsAuthenticated(),
            IsTeacherOrAdmin(),
            IsVerified(),
        ]

    def get_queryset(self):
        """
        Teachers: list Grade they are linked with.
        Admin/Students/Anonymous: list all Grade.
        """
        user = self.request.user

        if not user.is_authenticated or not hasattr(user, "teacher_profile"):
            return Grade.objects.all().order_by("level")

        return Grade.objects.filter(teacher_profiles=user.teacher_profile).order_by(
            "level"
        )
