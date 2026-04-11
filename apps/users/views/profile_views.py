"""Profile retrieval and management endpoints"""

from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from apps.users.models import TeacherProfile, StudentProfile, ParentProfile
from apps.users.serializers.update_user_profile_serializer import (
    TeacherProfileUpdateSerializer,
    StudentProfileUpdateSerializer,
    ParentProfileUpdateSerializer,
    ParentFullProfileSerializer,
)
from apps.core.permissions import IsVerified


class TeacherProfileView(generics.RetrieveUpdateAPIView):
    """
    GET: Retrieve current logged-in teacher's profile
    PATCH: Update current logged-in teacher's profile
    """

    serializer_class = TeacherProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_object(self):
        try:
            profile = TeacherProfile.objects.get(user=self.request.user)
        except TeacherProfile.DoesNotExist:
            raise PermissionDenied("No teacher profile found for this user.")
        return profile

    def get(self, request, *args, **kwargs):
        """Retrieve current teacher profile"""
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """Partial update of current teacher profile"""
        return self.partial_update(request, *args, **kwargs)


class StudentProfileView(generics.RetrieveUpdateAPIView):
    """
    GET: Retrieve current logged-in student's profile
    PATCH: Update current logged-in student's profile
    """

    serializer_class = StudentProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_object(self):
        try:
            profile = StudentProfile.objects.get(user=self.request.user)
        except StudentProfile.DoesNotExist:
            raise PermissionDenied("No student profile found for this user.")
        return profile

    def get(self, request, *args, **kwargs):
        """Retrieve current student profile"""
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """Partial update of current student profile"""
        return self.partial_update(request, *args, **kwargs)


class ParentProfileView(generics.RetrieveUpdateAPIView):
    """
    GET: Retrieve current logged-in parent's profile
    PATCH: Update current logged-in parent's profile
    """

    serializer_class = ParentProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_object(self):
        try:
            profile = ParentProfile.objects.get(user=self.request.user)
        except ParentProfile.DoesNotExist:
            raise PermissionDenied("No parent profile found for this user.")
        return profile

    def get(self, request, *args, **kwargs):
        """Retrieve current parent profile"""
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """Partial update of current parent profile"""
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """Full update of current parent profile."""
        return self.update(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Compatibility: treat POST as partial update for legacy frontend clients."""
        return self.partial_update(request, *args, **kwargs)


class ParentFullProfileView(generics.RetrieveAPIView):
    """Return the full parent profile including children and wallet summary."""

    serializer_class = ParentFullProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_object(self):
        try:
            return ParentProfile.objects.select_related("user").prefetch_related("children__user", "children__grade", "children__school").get(user=self.request.user)
        except ParentProfile.DoesNotExist:
            raise PermissionDenied("No parent profile found for this user.")


class ParentChildrenView(generics.ListAPIView):
    """
    GET: List all children for current logged-in parent
    """

    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Get children for current parent"""
        parent_id = self.kwargs.get("parent_id") or self.request.query_params.get("parent_id")

        if parent_id and parent_id not in ("undefined", "null", ""):
            parent = ParentProfile.objects.filter(id=parent_id).first()
            if parent:
                return parent.children.all()

        if getattr(self.request.user, "is_authenticated", False) and hasattr(
            self.request.user, "parent_profile"
        ):
            return self.request.user.parent_profile.children.all()

        return StudentProfile.objects.none()

    def get_serializer_class(self):
        return StudentProfileUpdateSerializer


class ParentRegisterStudentView(generics.CreateAPIView):
    """
    POST: Parent registers/creates a student account
    Automatically links the created student to the parent
    """

    permission_classes = [permissions.AllowAny]

    def _resolve_parent_profile(self):
        parent_id = self.kwargs.get("parent_id") or self.request.data.get("parent_id")

        if parent_id and parent_id not in ("undefined", "null", ""):
            try:
                return ParentProfile.objects.get(id=parent_id)
            except ParentProfile.DoesNotExist:
                pass

        if hasattr(self.request.user, "parent_profile"):
            return self.request.user.parent_profile

        return None

    def post(self, request, *args, **kwargs):
        """Register/create a student and link to current parent"""
        from apps.users.serializers.user_profile_serializer import (
            StudentRegistrationSerializer,
        )
        from apps.users.models import ParentChild

        # Create user serializer for registration
        serializer = StudentRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Create user with student role
            user = serializer.save(role="student")

            parent_profile = self._resolve_parent_profile()
            if not parent_profile:
                return Response(
                    {"error": "Parent profile not found. Provide a valid parent_id or authenticate as a parent."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Get or create student profile
            student_profile, created = StudentProfile.objects.get_or_create(user=user)

            # Link parent to student
            ParentChild.objects.get_or_create(
                parent=parent_profile, child=student_profile
            )

            return Response(
                {
                    "message": "Student registered and linked to parent",
                    "student": {
                        "id": student_profile.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
