from rest_framework import serializers
from djmoney.contrib.django_rest_framework import MoneyField

from apps.school.models import (
    Course, 
    Topic, Subtopic
    )

class CourseSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(
        source="subject.name", 
        read_only=True
    )
    grade_name = serializers.CharField(
        source="grade.name", 
        read_only=True
    )
    teacher_name = serializers.CharField(
        source="teacher.user.get_full_name", 
        read_only=True
    )
    price = MoneyField(
        max_digits=10, 
        decimal_places=2,
        default_currency="KES"
    )

    class Meta:
        model = Course
        fields = [
            "id","title","description",
            "subject","subject_name",
            "grade","grade_name","price",
            "is_active","code","cover_image",
            "teacher","teacher_name","created_at",
            "updated_at",'country', 'is_universal',
        ]
        read_only_fields = [
            "id", "created_at", 
            "updated_at", "teacher_name"
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user

        if hasattr(user, "teacher_profile") and not user.is_staff:
            if "teacher" in attrs and attrs["teacher"] != user.teacher_profile:
                raise serializers.ValidationError(
                    "You can only create courses" \
                    " under your own profile."
                )
            attrs["teacher"] = user.teacher_profile

        if user.is_staff and not attrs.get("teacher"):
            raise serializers.ValidationError(
                "Admin must assign a teacher" \
                " when creating a course."
            )

        if not attrs.get("subject"):
            raise serializers.ValidationError("Subject is required.")

        is_universal = attrs.get("is_universal", False)
        country = attrs.get("country")

        if is_universal:
            if country:
                raise serializers.ValidationError({
                    "country": "Universal courses "
                    "must not include a country."
                })
            attrs["country"] = None

        else:
            if not country:
                raise serializers.ValidationError({
                    "country": "Country is required "
                    "for non-universal courses."
                })

        return attrs


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = [
            "id", "course", ""
            "title", "description",
            "content_file", "order"
        ]

    def validate_course(self, value):
        user = self.context["request"].user
        if hasattr(user, "teacher_profile") and not user.is_staff:
            if value.teacher != user.teacher_profile:
                raise serializers.ValidationError(
                    "You cannot add topics " \
                    "to a course you don't own."
                )
        return value
    
    def get_content_file_url(self, obj):
        if obj.content_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.content_file.url)
            return obj.content_file.url
        return None
    
class SubtopicSerializer(serializers.ModelSerializer):
    content_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Subtopic
        fields = ["id", "topic", "title", "content", "content_file_url", "order"]

    def validate(self, attrs):
        user = self.context["request"].user
        topic = attrs.get("topic")

        if not attrs.get("content") and not attrs.get("content_file"):
            raise serializers.ValidationError(
                "You must provide either text content or upload a file."
            )

        if hasattr(user, "teacher_profile") and not user.is_staff:
            if topic.course.teacher != user.teacher_profile:
                raise serializers.ValidationError(
                    "You cannot add subtopics to a topic you don't own."
                )

        return attrs

    def get_content_file_url(self, obj):
        if obj.content_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.content_file.url)
            return obj.content_file.url
        return None


class CourseNestedSerializer(serializers.ModelSerializer):
    topics = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "price",
            "grade",
            "subject",
            "teacher",
            "topics",
        ]

    def get_topics(self, obj):
        topics = obj.topics.prefetch_related("subtopics").all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "content_file_url":self.get_file_url(t),
                "order": t.order,
                "subtopics": [
                    {
                        "id": st.id,
                        "title": st.title,
                        "content": st.content,
                        "content_file_url": self.get_file_url(st),
                        "order": st.order,
                    }
                    for st in t.subtopics.all()
                ],
            }
            for t in topics
        ]

    def get_file_url(self, subtopic):
        if subtopic.content_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(subtopic.content_file.url)
            return subtopic.content_file.url
        return None
