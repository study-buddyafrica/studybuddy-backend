from datetime import timedelta
import uuid

from django.db.models import Avg, Count
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsVerified
from apps.school.models import SessionBooking
from apps.users.models import (
    Availability,
    StudentProfile,
    TeacherProfile,
    TeacherRating,
)


class StudentPerformanceView(APIView):
    """Compatibility endpoint for frontend performance dashboard."""

    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def _resolve_student(self, request, student_id):
        if student_id in (None, "", "undefined", "null"):
            if hasattr(request.user, "student_profile"):
                return request.user.student_profile
            return None

        try:
            student = StudentProfile.objects.select_related("user").get(id=student_id)
        except StudentProfile.DoesNotExist:
            return None

        if request.user.is_staff or request.user.is_superuser:
            return student

        if (
            hasattr(request.user, "student_profile")
            and request.user.student_profile.id == student.id
        ):
            return student

        if (
            hasattr(request.user, "parent_profile")
            and request.user.parent_profile.children.filter(id=student.id).exists()
        ):
            return student

        return None

    def get(self, request, student_id=None):
        student = self._resolve_student(request, student_id)
        if student is None:
            return Response(
                {
                    "detail": "Student not found for this request.",
                    "lessons_completed": 0,
                    "total_study_time_hours": 0,
                    "avg_teacher_rating": 0,
                    "subject_performance": [],
                },
                status=status.HTTP_200_OK,
            )

        completed_bookings = SessionBooking.objects.filter(
            student=student,
            status="completed",
        ).select_related("course__subject", "teacher__user")

        total_minutes = 0
        for booking in completed_bookings:
            if booking.scheduled_start and booking.scheduled_end:
                delta = booking.scheduled_end - booking.scheduled_start
                total_minutes += max(int(delta.total_seconds() // 60), 0)

        avg_rating = (
            TeacherRating.objects.filter(student=student)
            .aggregate(avg=Avg("rating"))
            .get("avg")
            or 0
        )

        subject_perf_qs = (
            completed_bookings.values("course__subject__name")
            .annotate(count=Count("id"))
            .order_by("course__subject__name")
        )

        subject_performance = [
            {
                "subject": row["course__subject__name"] or "Unknown",
                "completed_lessons": row["count"],
            }
            for row in subject_perf_qs
        ]

        payload = {
            "student_id": str(student.id),
            "lessons_completed": completed_bookings.count(),
            "total_study_time_hours": round(total_minutes / 60, 2),
            "avg_teacher_rating": round(float(avg_rating), 2),
            "subject_performance": subject_performance,
        }
        return Response(payload, status=status.HTTP_200_OK)


class CompletedLessonsView(APIView):
    """Compatibility endpoint for frontend completed lessons list."""

    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def _resolve_student(self, request, student_id):
        if student_id in (None, "", "undefined", "null"):
            if hasattr(request.user, "student_profile"):
                return request.user.student_profile
            return None

        try:
            student = StudentProfile.objects.select_related("user").get(id=student_id)
        except StudentProfile.DoesNotExist:
            return None

        if request.user.is_staff or request.user.is_superuser:
            return student

        if (
            hasattr(request.user, "student_profile")
            and request.user.student_profile.id == student.id
        ):
            return student

        if (
            hasattr(request.user, "parent_profile")
            and request.user.parent_profile.children.filter(id=student.id).exists()
        ):
            return student

        return None

    def get(self, request, student_id=None):
        student = self._resolve_student(request, student_id)
        if student is None:
            return Response(
                {"completed_lessons": [], "total": 0}, status=status.HTTP_200_OK
            )

        bookings = (
            SessionBooking.objects.filter(student=student, status="completed")
            .select_related("course__subject", "teacher__user")
            .order_by("-scheduled_start")
        )

        lessons = []
        for booking in bookings:
            duration_hours = 0
            if booking.scheduled_start and booking.scheduled_end:
                delta = booking.scheduled_end - booking.scheduled_start
                duration_hours = round(max(delta.total_seconds(), 0) / 3600, 2)

            lessons.append(
                {
                    "id": str(booking.id),
                    "course": booking.course.title if booking.course else None,
                    "subject": booking.course.subject.name
                    if booking.course and booking.course.subject
                    else None,
                    "teacher": booking.teacher.user.first_name
                    if booking.teacher and booking.teacher.user
                    else None,
                    "scheduled_start": booking.scheduled_start,
                    "scheduled_end": booking.scheduled_end,
                    "duration_hours": duration_hours,
                    "status": booking.status,
                }
            )

        return Response(
            {"completed_lessons": lessons, "total": len(lessons)},
            status=status.HTTP_200_OK,
        )


class SubmitTimeRangeView(APIView):
    """Compatibility endpoint for frontend lesson timer submissions."""

    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def post(self, request, item_id=None):
        payload = {
            "item_id": item_id,
            "start_time": request.data.get("start_time"),
            "end_time": request.data.get("end_time"),
            "duration_seconds": request.data.get("duration_seconds"),
            "status": "recorded",
        }
        return Response(payload, status=status.HTTP_200_OK)


class AvailableTimesView(APIView):
    """Compatibility endpoint for frontend teacher availability lookup."""

    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def _resolve_teacher(self, teacher_id):
        if teacher_id in (None, "", "undefined", "null"):
            return None

        try:
            parsed_id = uuid.UUID(str(teacher_id))
        except (ValueError, TypeError, AttributeError):
            return None

        teacher = TeacherProfile.objects.filter(id=parsed_id).first()
        if teacher:
            return teacher

        # Legacy clients sometimes pass non-UUID identifiers.
        return None

    def get(self, request, teacher_id=None):
        teacher = self._resolve_teacher(teacher_id)
        if teacher is None:
            return Response(
                {"teacher_id": teacher_id, "available_times": [], "total": 0},
                status=status.HTTP_200_OK,
            )

        slots = (
            Availability.objects.filter(teacher=teacher, is_blocked=False)
            .order_by("date")
            .values("id", "date", "end_date")
        )

        available_times = [
            {
                "id": str(slot["id"]),
                "start": slot["date"],
                "end": slot["end_date"],
            }
            for slot in slots
        ]

        return Response(
            {
                "teacher_id": str(teacher.id),
                "available_times": available_times,
                "total": len(available_times),
            },
            status=status.HTTP_200_OK,
        )
