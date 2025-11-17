from rest_framework import generics, permissions

from apps.school.models import RevisionMaterial, Assessment
from apps.core.permissions import IsVerified, IsTeacherOrAdmin
from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.school.serializers.assessments_serializer import(
    RevisionMaterialSerializer,
    AssessmentSerializer
)

class RevisionMaterialCreateListView(generics.ListCreateAPIView):
    """
    - Teachers: List & create materials they uploaded
    - Admins: List & create all materials
    """
    serializer_class = RevisionMaterialSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = RevisionMaterial.objects.select_related("course", "uploaded_by__user")
        if hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(uploaded_by=user.teacher_profile)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, "teacher_profile") and not user.is_staff:
            serializer.save(uploaded_by=user.teacher_profile)
        else:
            serializer.save()


class AssessmentCreateListView(generics.ListCreateAPIView):
    """
    - Teachers: List & create assessments for their courses
    - Admins: List & create all assessments
    Supports nested creation of questions and choices.
    """
    serializer_class = AssessmentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsVerified, IsTeacherOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = Assessment.objects.select_related("course", "teacher__user") \
                               .prefetch_related("questions__choices")
        if hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(teacher=user.teacher_profile)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, "teacher_profile") and not user.is_staff:
            serializer.save(teacher=user.teacher_profile)
        else:
            serializer.save()


class AssessmentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    - Teachers: Retrieve & update their assessments
    - Admins: Retrieve & update any assessment
    Supports nested update of questions and choices.
    """
    serializer_class = AssessmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified, IsTeacherOrAdmin]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = Assessment.objects.select_related("course", "teacher__user") \
                               .prefetch_related("questions__choices")
        if hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(teacher=user.teacher_profile)
        return qs
