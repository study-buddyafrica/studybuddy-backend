from rest_framework import viewsets
from rest_framework import permissions

from apps.school.serializers.subjects_serializer import SubjectSerializer
from apps.core.permissions import IsTeacherOrAdmin, IsVerified
from apps.school.models import Subject


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
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
        Teachers: list subjects they are linked with.
        Admin/Students/Anonymous: list all subjects.
        """
        user = self.request.user

        if not user.is_authenticated or not hasattr(user, "teacher_profile"):
            return Subject.objects.all().order_by("name")

        return Subject.objects.filter(teacher_profiles=user.teacher_profile).order_by(
            "name"
        )
