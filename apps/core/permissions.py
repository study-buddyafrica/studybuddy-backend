from rest_framework import permissions
from rest_framework.permissions import BasePermission
from apps.users.models import ParentProfile,ParentChild,StudentProfile
from apps.school.models import CourseEnrollment

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

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    - Admin: full access
    - Normal users: read-only (GET only)
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_superuser)


class IsAdminOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (
            request.user.is_staff or request.user.is_superuser
        )


from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTeacherAdminOrLeadStudent(BasePermission):
    """
    - Teachers/Admins: full access
    - Students: read-only AND only their own lead records
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated

        return request.user.is_staff or hasattr(request.user, "teacher_profile")

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        if hasattr(request.user, "teacher_profile"):
            return obj.course.teacher == request.user.teacher_profile

        if hasattr(request.user, "student_profile"):
            return obj.student_profile == request.user.student_profile

        return False


class IsPeerSessionManager(BasePermission):
    """
    - Admin: full access
    - Teacher: manage own course sessions
    - Lead student: manage sessions they created
    - Enrolled students: read-only
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        if hasattr(user, "teacher_profile"):
            return obj.course.teacher == user.teacher_profile
        if hasattr(user, "student_profile"):
            if request.method in SAFE_METHODS:
                return CourseEnrollment.objects.filter(
                    student=user.student_profile, course=obj.course, is_active=True
                ).exists()
            return obj.created_by == user
        return False
