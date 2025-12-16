import uuid
from rest_framework import serializers
from django.core.exceptions import ValidationError

from apps.core.utils.dailyco import DailyCoAPI
from apps.school.serializers.livesession_serializer import DEFAULT_WHITEBOARD_LINK
from apps.school.models import (
    Course, LiveSession,
    CourseEnrollment
)

class CourseLiveSessionCreateSerializer(serializers.ModelSerializer):
    course_id = serializers.UUIDField(write_only=True)

    teacher_meeting_link = serializers.CharField(read_only=True)
    student_meeting_link = serializers.CharField(read_only=True)
    whiteboard_link = serializers.URLField(read_only=True)

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "course_id",
            "title",
            "description",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
            "started_at",
            "ended_at",
        ]
        read_only_fields = [
            "id",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        teacher = request.user.teacher_profile
        course_id = validated_data.pop("course_id")
        try:
            course = Course.objects.only("id").get(id=course_id, teacher=teacher)
        except Course.DoesNotExist:
            raise ValidationError("You do not own this course.")

        enrolled_students = CourseEnrollment.objects.filter(
            course=course, is_active=True
        ).select_related("student__user")

        if not enrolled_students.exists():
            raise ValidationError("No enrolled students for this course.")

        daily_api = DailyCoAPI()
        room_name = f"course_{course.id.hex[:8]}_{uuid.uuid4().hex[:6]}"

        room = daily_api.create_room(
            name=room_name,
            end_time=validated_data["ended_at"],
            properties={
                "enable_chat": True,
                "enable_screenshare": True,
                "enable_people_ui": True,
                "enable_prejoin_ui": True,
            },
        )
        teacher_token = daily_api.create_owner_token(
            room_name=room_name,
            user_id=str(teacher.id),
            user_name=f"{teacher.user.first_name} {teacher.user.last_name}",
        )

        student_token = daily_api.create_participant_token(
            room_name=room_name, 
            user_id=None,
            user_name="Student"
        )

        session = LiveSession.objects.create(
            course=course,
            teacher=teacher,
            teacher_meeting_link=teacher_token["room_url"],
            student_meeting_link=student_token["room_url"],
            whiteboard_link=DEFAULT_WHITEBOARD_LINK,
            started_at=validated_data["started_at"],
            ended_at=validated_data["ended_at"],
            title=validated_data["title"],
            description=validated_data.get("description", ""),
        )

        return session
