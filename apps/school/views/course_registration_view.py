from rest_framework import generics, permissions
from django.db.models import Q
from django.core.cache import cache
from rest_framework.response import Response

from apps.core.permissions import IsTeacherOrAdmin, IsVerified
from apps.core.utils.cache import cache_get_or_set      
from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.school.models import (
    Course, Topic,Subtopic
)
from apps.school.serializers.course_registration_serializer import (
    CourseSerializer, TopicSerializer,CoursePublicSerializer,
    SubtopicSerializer, CourseNestedSerializer
)


class CourseCreateListView(generics.ListCreateAPIView):
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                permissions.IsAuthenticated(),
                IsTeacherOrAdmin(),
                IsVerified(),
            ]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user

        qs = Course.objects.select_related(
            "subject", "grade", "teacher__user"
        ).prefetch_related("topics__subtopics")

        # Public visitor
        if not user.is_authenticated:
            return qs.order_by("title")

        # Admin
        if user.is_staff:
            return qs.order_by("title")

        # Teacher
        if hasattr(user, "teacher_profile"):
            return qs.filter(
                teacher=user.teacher_profile
            ).order_by("title")

        # Student
        if hasattr(user, "student_profile"):
            student_country = user.student_profile.country
            return qs.filter(
                Q(is_universal=True) |
                Q(country=student_country)
            ).order_by("title")

        return qs.order_by("title")

    def list(self, request, *args, **kwargs):
        """Apply intelligent caching only for GET requests."""
        user = request.user

        # Build dynamic cache keys
        if not user.is_authenticated:
            cache_key = "courses_public"
        elif user.is_staff:
            cache_key = "courses_admin"
        elif hasattr(user, "teacher_profile"):
            cache_key = f"courses_teacher_{user.teacher_profile.id}"
        elif hasattr(user, "student_profile"):
            cache_key = (
                f"courses_student_country_{user.student_profile.country}"
            )
        else:
            cache_key = "courses_default"

        # Retrieve cached paginated results
        def fetch_data():
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data).data

        response_data = cache_get_or_set(cache_key, fetch_data, timeout=600)

        return Response(response_data)

    def get_serializer_class(self):
        user = self.request.user

        if self.request.method == "POST":
            return CourseSerializer

        if not user.is_authenticated:
            return CoursePublicSerializer

        if user.is_staff:
            return CourseNestedSerializer

        if hasattr(user, "teacher_profile"):
            return CourseNestedSerializer

        return CoursePublicSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, "teacher_profile") and not user.is_staff:
            serializer.save(teacher=user.teacher_profile)
        else:
            serializer.save()



class TopicCreateListView(generics.ListCreateAPIView):
    serializer_class = TopicSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [
        permissions.IsAuthenticated,
        IsTeacherOrAdmin, IsVerified
    ]

    def get_queryset(self):
        user = self.request.user
        qs = Topic.objects.select_related("course", "course__teacher__user")

        if hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(course__teacher=user.teacher_profile)

        return qs.order_by("course__title", "order")

class SubtopicCreateListView(generics.ListCreateAPIView):
    serializer_class = SubtopicSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [
        permissions.IsAuthenticated,
        IsTeacherOrAdmin,IsVerified
    ]

    def get_queryset(self):
        user = self.request.user
        qs = Subtopic.objects.select_related(
            "topic", 
            "topic__course", 
            "topic__course__teacher__user"
        )

        if hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(topic__course__teacher=user.teacher_profile)

        return qs.order_by("topic__title", "order")