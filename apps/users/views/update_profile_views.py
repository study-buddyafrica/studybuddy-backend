from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from apps.users.models import TeacherProfile, StudentProfile, ParentProfile
from apps.users.serializers.update_user_profile_serializer import (
    TeacherProfileUpdateSerializer,
    StudentProfileUpdateSerializer,
    ParentProfileUpdateSerializer,
)
from apps.core.permissions import (
    CanEditStudentProfile,
    CanEditParentProfile,
    IsVerified,
)
from apps.users.views.profile_views import _resolve_parent_profile


class TeacherProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    Allows logged-in teacher to view or update their own profile.
    """

    serializer_class = TeacherProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_object(self):
        try:
            profile = TeacherProfile.objects.get(user=self.request.user)
        except TeacherProfile.DoesNotExist:
            raise PermissionDenied("No teacher profile found for this user.")
        return profile


class StudentProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    Allows admin, student, or related parent to view/update the student profile.
    """

    queryset = StudentProfile.objects.select_related(
        "user", "grade", "school"
    ).prefetch_related("parents")
    serializer_class = StudentProfileUpdateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        CanEditStudentProfile,
        IsVerified,
    ]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return self.queryset
        parent_profile = getattr(user, "parent_profile", None)
        if parent_profile:
            return self.queryset.filter(parents=parent_profile)

        student_profile = getattr(user, "student_profile", None)
        if student_profile:
            return self.queryset.filter(user=user)
        return StudentProfile.objects.none()


class ParentProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    Allows admins or the parent themself to retrieve/update their profile.
    """

    queryset = ParentProfile.objects.select_related("user").prefetch_related("children")
    serializer_class = ParentProfileUpdateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        CanEditParentProfile,
        IsVerified,
    ]
    lookup_field = "id"

    def get_object(self):
        query_params = getattr(self.request, "query_params", self.request.GET)
        parent_id = self.kwargs.get("id") or query_params.get("id")
        parent = _resolve_parent_profile(parent_id, self.request.user)

        if not parent:
            raise PermissionDenied("No parent profile found for this user.")

        if not (self.request.user.is_staff or self.request.user.is_superuser):
            if (
                not hasattr(self.request.user, "parent_profile")
                or parent.user != self.request.user
            ):
                raise PermissionDenied(
                    "You are not allowed to access this parent profile."
                )

        return parent

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return self.queryset
        elif hasattr(user, "parent_profile"):
            return self.queryset.filter(user=user)
        return ParentProfile.objects.none()
