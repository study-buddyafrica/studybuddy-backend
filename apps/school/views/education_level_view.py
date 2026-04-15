from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from apps.school.models import EducationLevel
from apps.school.serializers.education_level_serializer import EducationLevelSerializer


class EducationLevelViewSet(viewsets.ModelViewSet):
    serializer_class = EducationLevelSerializer
    queryset = EducationLevel.objects.all().order_by("name")

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "detail": (
                    'Method "POST" not allowed. '
                    "Education levels are managed by system migrations."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {
                "detail": (
                    'Method "PUT" not allowed. '
                    "Education levels are managed by system migrations."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {
                "detail": (
                    'Method "PATCH" not allowed. '
                    "Education levels are managed by system migrations."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "detail": (
                    'Method "DELETE" not allowed. '
                    "Education levels are managed by system migrations."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
