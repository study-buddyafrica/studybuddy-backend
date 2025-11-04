from rest_framework import permissions
from apps.users.models import ParentProfile,ParentChild,StudentProfile

class CanEditParentProfile(permissions.BasePermission):
    """
    Permission for editing parent profiles.
    - Admins/superusers can edit all.
    - A parent can only edit their own profile.
    """

    def has_object_permission(self, request, view, obj: ParentProfile):
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        if hasattr(user, "parent_profile") and obj.user == user:
            return True
        return False
    
class CanEditStudentProfile(permissions.BasePermission):
    """
    Allows access if:
    - user is admin/superuser, OR
    - user is the student themself, OR
    - user is a parent linked to the student
    """

    def has_object_permission(self, request, view, obj: StudentProfile):
        user = request.user

        # Admins or superusers
        if user.is_staff or user.is_superuser:
            return True

        # Student editing their own profile
        if hasattr(user, "student_profile") and obj.user == user:
            return True

        # Parent linked to this student
        if hasattr(user, "parent_profile"):
            return ParentChild.objects.filter(
                parent=user.parent_profile, child=obj
            ).exists()

        return False
