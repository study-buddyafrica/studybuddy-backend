from rest_framework import generics, permissions
from django.db.models import Q

from apps.core.permissions import IsTeacherOrAdmin, IsVerified
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
                IsTeacherOrAdmin(),IsVerified()
            ]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related(
            "subject", "grade", "teacher__user"
        ).prefetch_related("topics__subtopics")

        if not user.is_authenticated:
            return qs.order_by("title")

        if user.is_staff:
            return qs.order_by("title")

        if hasattr(user, "teacher_profile"):
            return qs.filter(teacher=user.teacher_profile).order_by("title")

        return qs.order_by("title")

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