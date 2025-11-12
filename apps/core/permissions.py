from rest_framework import permissions
from rest_framework.permissions import BasePermission
from apps.users.models import ParentProfile,ParentChild,StudentProfile

class IsVerified(permissions.BasePermission):
    """
    Allows access only to verified users,
    except for admins or superusers.
    """

    message = (
    "Your account "
    "is not verified yet. "
    "Please verify your email "
    "before proceeding."
    )

    def has_permission(self, request, view):
        user = request.user

        if user and (user.is_staff or user.is_superuser):
            return True

        return bool(
            user and user.is_authenticated 
            and getattr(user, "account_confirmed", 
            False)
            )

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

        if user.is_staff or user.is_superuser:
            return True

        if hasattr(user, "student_profile") and obj.user == user:
            return True

        if hasattr(user, "parent_profile"):
            return ParentChild.objects.filter(
                parent=user.parent_profile, child=obj
            ).exists()

        return False
    

class IsStudent(permissions.BasePermission):
    """Custom permission — only allow logged-in students."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "student_profile")
        )


class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            hasattr(request.user, "teacher_profile")
            or request.user.is_superuser
            or request.user.is_staff
        )