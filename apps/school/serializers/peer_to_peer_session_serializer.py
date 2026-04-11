import uuid
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers

from apps.core.utils.dailyco import DailyCoAPI
from apps.school.models import CourseEnrollment, LiveSession
from apps.school.serializers.livesession_serializer import DEFAULT_WHITEBOARD_LINK


class PeerLiveSessionSerializer(serializers.ModelSerializer):
    duration_hours = serializers.FloatField(write_only=True)
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField(read_only=True)
    course_title = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "course",
            "course_title",
            "teacher",
            "teacher_name",
            "title",
            "description",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
            "started_at",
            "duration_hours",
            "ended_at",
        ]
        read_only_fields = [
            "id",
            "course_title",
            "teacher_name",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
            "started_at",
            "ended_at",
        ]

    def get_course_title(self, obj):
        """Return course title"""
        return obj.course.title if obj.course else ""

    def get_teacher_name(self, obj):
        """Return teacher full name"""
        if obj.teacher and obj.teacher.user:
            return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}"
        return ""

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        course = attrs.get("course")

        if not course:
            raise serializers.ValidationError("Course is required.")

        if user.is_staff:
            return attrs

        if hasattr(user, "teacher_profile"):
            if course.teacher != user.teacher_profile:
                raise serializers.ValidationError(
                    "You can only create sessions for your own courses."
                )
            return attrs

        if hasattr(user, "student_profile"):
            # Any authenticated student can create a peer session for a course.
            # The invite flow is handled client-side by sharing the room URL.
            return attrs

        raise serializers.ValidationError(
            "You are not allowed to create live sessions."
        )

    def create(self, validated_data):
        user = self.context["request"].user
        course = validated_data.get("course")
        title = validated_data.get("title")
        description = validated_data.get("description")
        duration_hours = validated_data.pop("duration_hours")
        started_at = validated_data.pop("started_at")

        ended_at = started_at + timedelta(hours=duration_hours)

        daily_api = DailyCoAPI()
        random_suffix = uuid.uuid4().hex[:6]
        room_name = f"peer_{course.id.hex[:8]}_{random_suffix}"

        room = daily_api.create_room(
            name=room_name,
            end_time=timezone.now() + timezone.timedelta(hours=2),
            properties={
                "enable_chat": True,
                "enable_screenshare": True,
                "start_audio_off": False,
                "start_video_off": False,
            },
        )

        teacher_token = daily_api.create_owner_token(
            room_name=room_name,
            user_id=str(course.teacher.id),
            user_name=f"{course.teacher.user.first_name} {course.teacher.user.last_name}",
        )

        student_token = daily_api.create_participant_token(
            room_name=room_name, user_id="student_group", user_name="Enrolled Students"
        )

        live_session = LiveSession.objects.create(
            course=course,
            teacher=course.teacher,
            title=title,
            description=description,
            teacher_meeting_link=teacher_token["room_url"],
            student_meeting_link=student_token["room_url"],
            whiteboard_link=DEFAULT_WHITEBOARD_LINK,
            started_at=started_at,
            ended_at=ended_at
        )

        return live_session
