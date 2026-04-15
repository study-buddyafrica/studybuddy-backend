from rest_framework import viewsets, permissions
from apps.users.models import Availability
from apps.users.serializers.availability_serializer import AvailabilitySerializer
from apps.core.permissions import IsTeacherOrAdmin


class AvailabilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher availability.
    
    Teachers can create, read, update, and delete their availability slots.
    Admin can view all availabilities.
    """
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]

    def get_queryset(self):
        """
        Filter availability based on user role:
        - Teachers see only their own availability
        - Admin sees all availability
        """
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return Availability.objects.select_related("teacher__user").all()
        
        if hasattr(user, "teacher_profile"):
            return Availability.objects.select_related("teacher__user").filter(
                teacher=user.teacher_profile
            )
        
        return Availability.objects.none()
