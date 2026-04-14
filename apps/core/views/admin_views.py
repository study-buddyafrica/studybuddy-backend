"""Admin dashboard and statistics endpoints"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from django.db.models import Count
from apps.core.models import User
from apps.users.models import TeacherProfile, StudentProfile
from apps.school.models import Course, Grade, Subject
from apps.core.permissions import IsVerified
from rest_framework.permissions import IsAdminUser


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_dashboard_stats(request):
    """
    GET: Admin dashboard statistics
    Returns counts and metrics for the admin dashboard
    """
    try:
        stats = {
            "total_users": User.objects.count(),
            "total_teachers": User.objects.filter(role="teacher").count(),
            "total_students": User.objects.filter(role="student").count(),
            "total_parents": User.objects.filter(role="parent").count(),
            "total_verified_teachers": TeacherProfile.objects.filter(
                is_verified=True
            ).count(),
            "total_courses": Course.objects.count(),
            "total_grades": Grade.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "students_by_grade": dict(
                StudentProfile.objects.values("grade__level")
                .annotate(count=Count("id"))
                .values_list("grade__level", "count")
            ),
        }
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_get_classes(request):
    """
    GET: Get all grades/classes in the system
    Returns all available grades with student counts
    """
    try:
        grades = (
            Grade.objects.annotate(
                student_count=Count("students", distinct=True),
                course_count=Count("courses", distinct=True),
            )
            .values("id", "level", "student_count", "course_count", "created_at")
            .order_by("level")
        )

        return Response(
            {"grades": list(grades), "total": grades.count()}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_list_users(request):
    """
    GET: List all users in the system
    Optional query params: role, is_active
    """
    try:
        queryset = User.objects.all()

        # Filter by role if provided
        role = request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        # Filter by active status if provided
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        users = queryset.values(
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "account_confirmed",
            "created_at",
        ).order_by("-created_at")

        return Response(
            {"users": list(users), "total": queryset.count()}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_list_teachers(request):
    """
    GET: List all teachers with their verification status
    Optional query params: is_verified
    """
    try:
        queryset = TeacherProfile.objects.select_related("user").all()

        # Filter by verification status if provided
        is_verified = request.query_params.get("is_verified")
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == "true")

        teachers = []
        for teacher in queryset:
            teachers.append(
                {
                    "id": str(teacher.id),
                    "user_id": str(teacher.user.id),
                    "email": teacher.user.email,
                    "first_name": teacher.user.first_name,
                    "last_name": teacher.user.last_name,
                    "is_verified": teacher.is_verified,
                    "verification_status": teacher.verification_status,
                    "experience": teacher.experience,
                    "hourly_rate": str(teacher.hourly_rate)
                    if teacher.hourly_rate
                    else None,
                    "created_at": teacher.created_at.isoformat(),
                }
            )

        return Response(
            {"teachers": teachers, "total": queryset.count()}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_list_students(request):
    """
    GET: List all students with their grade/school info
    Optional query params: grade_id, school_id
    """
    try:
        queryset = StudentProfile.objects.select_related(
            "user", "grade", "school"
        ).all()

        # Filter by grade if provided
        grade_id = request.query_params.get("grade_id")
        if grade_id:
            queryset = queryset.filter(grade_id=grade_id)

        # Filter by school if provided
        school_id = request.query_params.get("school_id")
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        students = []
        for student in queryset:
            students.append(
                {
                    "id": str(student.id),
                    "user_id": str(student.user.id),
                    "email": student.user.email,
                    "first_name": student.user.first_name,
                    "last_name": student.user.last_name,
                    "grade": student.grade.level if student.grade else None,
                    "school": student.school.name if student.school else None,
                    "enrollment_date": student.enrollment_date.isoformat(),
                    "created_at": student.created_at.isoformat(),
                }
            )

        return Response(
            {"students": students, "total": queryset.count()}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_get_subjects(request):
    """GET: Admin endpoint returning subjects with basic metadata."""
    try:
        subjects = Subject.objects.values(
            "id", "name", "description", "created_at"
        ).order_by("name")
        return Response(
            {"subjects": list(subjects), "total": subjects.count()},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsVerified])
def get_classes(request):
    """Compatibility endpoint for frontend class listing."""
    grades = Grade.objects.values("id", "level").order_by("level")
    return Response(
        {"grades": list(grades), "total": grades.count()}, status=status.HTTP_200_OK
    )


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, IsVerified])
def get_subjects(request):
    """Compatibility endpoint for frontend subject listing."""
    subjects = Subject.objects.values("id", "name", "description").order_by("name")
    return Response(
        {"subjects": list(subjects), "total": subjects.count()},
        status=status.HTTP_200_OK,
    )
