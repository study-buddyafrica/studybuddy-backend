from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.users.models import TeacherProfile
from apps.school.models import Topic, Subtopic, Course
from rest_framework import serializers


class ContentFileSerializer(serializers.Serializer):
    """Serializer for content files (videos) from topics and subtopics"""
    id = serializers.UUIDField()
    type = serializers.CharField()  # 'topic' or 'subtopic'
    title = serializers.CharField()
    content_file = serializers.SerializerMethodField()
    course_id = serializers.UUIDField()
    course_title = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_content_file(self, obj):
        request = self.context.get("request")
        if obj.get("content_file") and request:
            return request.build_absolute_uri(obj["content_file"].url)
        return obj.get("content_file")


class TeacherVideosView(generics.ListAPIView):
    """
    Gets all videos (content files) for a specific teacher's courses.
    
    Path: /lessons/api/videos/teacher/{teacher_id}
    """
    serializer_class = ContentFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        teacher_id = self.kwargs.get("teacher_id")
        
        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
        except TeacherProfile.DoesNotExist:
            return []

        # Get all courses taught by this teacher
        courses = Course.objects.filter(teacher=teacher)
        
        # Collect topics and subtopics with content_file
        items = []
        
        for course in courses:
            # Get topics with content_file
            topics = Topic.objects.filter(course=course, content_file__isnull=False).exclude(content_file="")
            for topic in topics:
                items.append({
                    "id": topic.id,
                    "type": "topic",
                    "title": topic.title,
                    "content_file": topic.content_file,
                    "course_id": course.id,
                    "course_title": course.title,
                    "created_at": topic.created_at,
                })

            # Get subtopics with content_file
            subtopics = Subtopic.objects.filter(topic__course=course, content_file__isnull=False).exclude(content_file="")
            for subtopic in subtopics:
                items.append({
                    "id": subtopic.id,
                    "type": "subtopic",
                    "title": subtopic.title,
                    "content_file": subtopic.content_file,
                    "course_id": course.id,
                    "course_title": course.title,
                    "created_at": subtopic.created_at,
                })
        
        return items

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
