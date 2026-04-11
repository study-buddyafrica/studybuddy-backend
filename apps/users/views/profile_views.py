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


class ParentChildrenView(generics.ListAPIView):
    """
    GET: List all children for current logged-in parent
    """

    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        """Get children for current parent"""
        try:
            parent = ParentProfile.objects.get(user=self.request.user)
            return parent.children.all()
        except ParentProfile.DoesNotExist:
            return StudentProfile.objects.none()

    def get_serializer_class(self):
        return StudentProfileUpdateSerializer
