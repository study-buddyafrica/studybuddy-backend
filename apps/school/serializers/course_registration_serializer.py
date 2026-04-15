from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from djmoney.contrib.django_rest_framework import MoneyField

from apps.school.models import Course, Topic, Subtopic
from apps.core.serializers import SanitizeHTMLMixin


class CourseSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["title", "description"]
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    education_level_name = serializers.CharField(
        source="education_level.name", read_only=True
    )
    teacher_name = serializers.CharField(
        source="teacher.user.get_full_name", read_only=True
    )
    price = MoneyField(max_digits=10, decimal_places=2, default_currency="KES")

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "subject_name",
            "grade",
            "grade_name",
            "education_level",
            "education_level_name",
            "price",
            "is_active",
            "cover_image",
            "teacher",
            "teacher_name",
            "created_at",
            "updated_at",
            "country",
            "is_universal",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "teacher_name"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user

        if hasattr(user, "teacher_profile") and not user.is_staff:
            if "teacher" in attrs and attrs["teacher"] != user.teacher_profile:
                raise serializers.ValidationError(
                    "You can only create courses under your own profile."
                )
            attrs["teacher"] = user.teacher_profile

        if user.is_staff and not attrs.get("teacher"):
            raise serializers.ValidationError(
                "Admin must assign a teacher when creating a course."
            )

        if not attrs.get("subject"):
            raise serializers.ValidationError("Subject is required.")

        is_universal = attrs.get("is_universal", False)
        country = attrs.get("country")

        if is_universal:
            if country:
                raise serializers.ValidationError(
                    {"country": "Universal courses must not include a country."}
                )
            attrs["country"] = None

        else:
            if not country:
                raise serializers.ValidationError(
                    {"country": "Country is required for non-universal courses."}
                )

        return attrs


class CoursePublicSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["title", "description"]
    teacher = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    education_level = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "price",
            "country",
            "is_universal",
            "teacher",
            "grade",
            "subject",
            "education_level",
        ]

    @extend_schema_field(serializers.DictField())
    def get_teacher(self, obj) -> dict | None:
        teacher = obj.teacher
        if not teacher:
            return None
        return {
            "first_name": teacher.user.first_name,
            "last_name": teacher.user.last_name,
            "country": teacher.user.country,
            "experience_in_years": teacher.experience,
        }

    @extend_schema_field(serializers.DictField())
    def get_grade(self, obj) -> dict | None:
        if obj.grade:
            return {"level": obj.grade.level}
        return None

    @extend_schema_field(serializers.DictField())
    def get_subject(self, obj) -> dict | None:
        if obj.subject:
            return {"name": obj.subject.name}
        return None

    @extend_schema_field(serializers.DictField())
    def get_education_level(self, obj) -> dict | None:
        if obj.education_level:
            return {"code": obj.education_level.code, "name": obj.education_level.name}
        return None


class CourseNestedSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["title", "description"]
    topics = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    education_level = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "price",
            "grade",
            "education_level",
            "subject",
            "teacher",
            "is_universal",
            "country",
            "topics",
        ]

    @extend_schema_field(serializers.DictField())
    def get_teacher(self, obj) -> dict | None:
        teacher = obj.teacher
        if not teacher:
            return None
        return {
            "first_name": teacher.user.first_name,
            "last_name": teacher.user.last_name,
            "country": teacher.user.country,
            "experience": teacher.experience,
        }

    @extend_schema_field(serializers.DictField())
    def get_grade(self, obj) -> dict | None:
        if obj.grade:
            return {"level": obj.grade.level}
        return None

    @extend_schema_field(serializers.DictField())
    def get_subject(self, obj) -> dict | None:
        if obj.subject:
            return {"name": obj.subject.name}
        return None

    @extend_schema_field(serializers.DictField())
    def get_education_level(self, obj) -> dict | None:
        if obj.education_level:
            return {"code": obj.education_level.code, "name": obj.education_level.name}
        return None

    @extend_schema_field(serializers.ListField())
    def get_topics(self, obj) -> list[dict]:
        topics = obj.topics.prefetch_related("subtopics").all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "content_file_url": self.get_file_url(t),
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

    def get_file_url(self, item):
        if item.content_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(item.content_file.url)
            return item.content_file.url
        return None


class TopicSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["title", "description"]

    class Meta:
        model = Topic
        fields = [
            "id",
            "course",
            "title",
            "description",
            "content_file",
            "order",
            "is_locked",
        ]

    def validate_course(self, value):
        user = self.context["request"].user
        if hasattr(user, "teacher_profile") and not user.is_staff:
            if value.teacher != user.teacher_profile:
                raise serializers.ValidationError(
                    "You cannot add topics to a course you don't own."
                )
        return value

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_content_file_url(self, obj) -> str | None:
        if obj.content_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.content_file.url)
            return obj.content_file.url
        return None


class SubtopicSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["title", "content"]
    content_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Subtopic
        fields = [
            "id",
            "topic",
            "title",
            "content",
            "content_file_url",
            "order",
            "is_locked",
        ]

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

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_content_file_url(self, obj) -> str | None:
        if obj.content_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.content_file.url)
            return obj.content_file.url
        return None
