from rest_framework import viewsets
from rest_framework import permissions

from apps.school.models import Subject
from apps.school.serializers.subjects_serializer import SubjectSerializer

from apps.core.permissions import IsTeacherOrAdmin, IsVerified
from apps.core.auth.views.pagination_view import StandardResultsSetPagination


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    pagination_class = StandardResultsSetPagination
    queryset = Subject.objects.all().order_by("name")

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
        Default: list all subjects for frontend dropdown compatibility.
        Optional: teachers can request only their linked subjects via ?mine=true.
        """
        user = self.request.user
        mine = str(self.request.GET.get("mine", "")).lower() in {
            "1",
            "true",
            "yes",
        }
        teacher_profile = getattr(user, "teacher_profile", None)

        if not mine or not user.is_authenticated or teacher_profile is None:
            return Subject.objects.all().order_by("name")

        return Subject.objects.filter(teacher_profiles=teacher_profile).order_by(
            "name"
        )
