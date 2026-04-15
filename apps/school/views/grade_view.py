from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

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
        Default: list all grades for frontend dropdown compatibility.
        Optional: teachers can request only their linked grades via ?mine=true.
        """
        user = self.request.user
        mine = str(self.request.query_params.get("mine", "")).lower() in {
            "1",
            "true",
            "yes",
        }

        if not mine or not user.is_authenticated or not hasattr(user, "teacher_profile"):
            return Grade.objects.all().order_by("level")

        return Grade.objects.filter(teacher_grades=user.teacher_profile).order_by(
            "level"
        )

    def create(self, request, *args, **kwargs):
        """
        Disable create method - grades are created automatically
        """
        return Response(
            {"detail": 'Method "POST" not allowed. Grades are created automatically.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        """
        Disable update method - grades are created automatically
        """
        return Response(
            {"detail": 'Method "PUT" not allowed. Grades are created automatically.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Disable partial update method - grades are created automatically
        """
        return Response(
            {"detail": 'Method "PATCH" not allowed. Grades are created automatically.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Disable delete method - grades are created automatically
        """
        return Response(
            {
                "detail": 'Method "DELETE" not allowed. Grades are created automatically.'
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
