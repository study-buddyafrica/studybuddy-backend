from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from apps.core.permissions import IsVerified
from apps.core.utils.cache import cache_get_or_set
from apps.school.models import CourseEnrollment, Course
from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.school.serializers.course_enrollment_serializer import (
    CourseEnrollmentSerializer,
    EnrolledStudentSerializer,
)


class CourseEnrollmentView(generics.ListCreateAPIView):
    """
    - Students: Enroll in courses and view their enrollments.
    - Teachers/Admins: View enrollments for their own courses.
    """

    serializer_class = CourseEnrollmentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        user = self.request.user
        qs = CourseEnrollment.objects.select_related(
            "course__teacher__user", "student__user", "transaction"
        ).prefetch_related(Prefetch("course__enrollments"))

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


class ListEnrolledStudentsView(generics.ListAPIView):
    """
    - Admin/Staff: View students enrolled in any course
    - Teacher: View students enrolled in their own course only
    """

    serializer_class = EnrolledStudentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    queryset = CourseEnrollment.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CourseEnrollment.objects.none()

        user = self.request.user
        course_id = self.kwargs.get("course_id")

        if not getattr(user, "is_authenticated", False) or not course_id:
            return CourseEnrollment.objects.none()

        course = get_object_or_404(Course, id=course_id)

        if hasattr(user, "teacher_profile") and course.teacher != user.teacher_profile:
            raise PermissionDenied("This course does not belong to you.")

        qs = (
            CourseEnrollment.objects.select_related(
                "student__user",
                "course__teacher__user",
            )
            .filter(course_id=course_id)
            .order_by("-purchased_at")
        )

        if user.is_staff or user.is_superuser:
            return qs

        if hasattr(user, "teacher_profile"):
            return qs.filter(course__teacher=user.teacher_profile)

        raise PermissionDenied("You are not allowed to view enrolled students.")


class ListEnrolledCourseView(generics.ListAPIView):
    serializer_class = CourseEnrollmentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    queryset = CourseEnrollment.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CourseEnrollment.objects.none()

        user = self.request.user

        if not getattr(user, "is_authenticated", False):
            return CourseEnrollment.objects.none()

        qs = (
            CourseEnrollment.objects.select_related(
                "student__user",
                "course__subject",
                "course__grade",
                "course__teacher__user",
            )
            .prefetch_related("course__topics__subtopics")
            .distinct()
        )

        if user.is_staff:
            return qs.order_by("course__title")

        if not hasattr(user, "student_profile"):
            return CourseEnrollment.objects.none()

        return qs.filter(student=user.student_profile).order_by("course__title")


class RetrieveEnrolledCourseView(generics.RetrieveAPIView):
    """
    Retrieve a single enrolled course with all related topics/subtopics.
    - Students: can only access their own enrollment
    - Admins/Staff: can access any enrollment
    """

    serializer_class = CourseEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    lookup_field = "enrollment_id"

    def get_queryset(self):
        return CourseEnrollment.objects.select_related(
            "student__user",
            "course__subject",
            "course__grade",
            "course__teacher__user",
        ).prefetch_related("course__topics__subtopics")

    def get_object(self):
        user = self.request.user
        enrollment_id = self.kwargs["enrollment_id"]
        qs = self.get_queryset()

        if user.is_staff or user.is_superuser:
            enrollment = get_object_or_404(qs, id=enrollment_id)
        else:
            enrollment = get_object_or_404(
                qs, id=enrollment_id, student=user.student_profile
            )

        cache_key = f"enrolled_course:{enrollment_id}:{user.id}"

        def fetch():
            serializer = self.get_serializer(enrollment)
            return serializer.data

        cached_data = cache_get_or_set(cache_key, fetch, timeout=60 * 10)  # 10 minutes

        return enrollment
