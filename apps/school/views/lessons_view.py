"""Lessons and learning content API endpoints"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.school.models import Course, Topic, Subtopic
from apps.school.serializers.course_registration_serializer import (
    CourseNestedSerializer,
    TopicSerializer,
    SubtopicSerializer,
)
from apps.core.permissions import IsVerified


class LessonsListView(generics.ListAPIView):
    """
    GET: List all lessons (courses with topics and subtopics)
    """

    permission_classes = [permissions.IsAuthenticated, IsVerified]
    serializer_class = CourseNestedSerializer

    def get_queryset(self):
        """Get all courses"""
        return (
            Course.objects.filter(is_active=True)
            .select_related("subject", "grade", "teacher__user")
            .prefetch_related("topics__subtopics")
            .all()
        )


class LessonsDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve a specific lesson (course with full content)
    """

    permission_classes = [permissions.IsAuthenticated, IsVerified]
    serializer_class = CourseNestedSerializer
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_queryset(self):
        """Get active courses"""
        return (
            Course.objects.filter(is_active=True)
            .select_related("subject", "grade", "teacher__user")
            .prefetch_related("topics__subtopics")
        )


class CourseTopicsListView(generics.ListAPIView):
    """
    GET: List all topics for a specific course
    """

    permission_classes = [permissions.IsAuthenticated, IsVerified]
    serializer_class = TopicSerializer

    def get_queryset(self):
        """Get topics for a specific course"""
        course_id = self.kwargs.get("course_id")
        return (
            Topic.objects.filter(course_id=course_id, course__is_active=True)
            .select_related("course")
            .all()
        )


class TopicSubtopicsListView(generics.ListAPIView):
    """
    GET: List all subtopics for a specific topic
    """

    permission_classes = [permissions.IsAuthenticated, IsVerified]
    serializer_class = SubtopicSerializer

    def get_queryset(self):
        """Get subtopics for a specific topic"""
        topic_id = self.kwargs.get("topic_id")
        return (
            Subtopic.objects.filter(topic_id=topic_id, topic__course__is_active=True)
            .select_related("topic")
            .all()
        )


class CourseDetailWithContentView(generics.RetrieveAPIView):
    """
    GET: Retrieve course with all topics and subtopics (same as LessonsDetailView)
    Included for completeness and semantic clarity
    """

    permission_classes = [permissions.IsAuthenticated, IsVerified]
    serializer_class = CourseNestedSerializer
    lookup_field = "id"
    lookup_url_kwarg = "course_id"

    def get_queryset(self):
        """Get active courses"""
        return (
            Course.objects.filter(is_active=True)
            .select_related("subject", "grade", "teacher__user")
            .prefetch_related("topics__subtopics")
        )
