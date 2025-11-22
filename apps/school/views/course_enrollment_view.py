from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from django.db.models import Prefetch

from apps.school.models import CourseEnrollment
from apps.school.serializers.course_enrollment_serializer import CourseEnrollmentSerializer
from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.core.permissions import IsVerified


class CourseEnrollmentView(generics.ListCreateAPIView):
    """
    - Students: Enroll in courses and view their enrollments.
    - Teachers/Admins: View enrollments for their own courses.
    """
    serializer_class = CourseEnrollmentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated,IsVerified]

    def get_queryset(self):
        user = self.request.user
        qs = (
            CourseEnrollment.objects
            .select_related("course__teacher__user", "student__user", "transaction")
            .prefetch_related(Prefetch("course__enrollments"))
        )

        if hasattr(user, "student_profile") and not user.is_staff:
            qs = qs.filter(student=user.student_profile)
        elif hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(course__teacher=user.teacher_profile)

        return qs.order_by("-purchased_at")

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, "student_profile"):
            raise PermissionDenied("Only students can enroll in courses.")

        serializer.context["request"] = self.request
        serializer.save(student=user.student_profile)

class ListEnrolledCourseView(generics.ListAPIView):
    serializer_class = CourseEnrollmentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        user = self.request.user

        qs = CourseEnrollment.objects.select_related(
            "student__user",
            "course__subject",
            "course__grade",
            "course__teacher__user",
        ).prefetch_related(
            "course__topics__subtopics"
        ).distinct()

        if user.is_staff:
            return qs.order_by("course__title")

        return qs.filter(student=user.student_profile).order_by("course__title")
