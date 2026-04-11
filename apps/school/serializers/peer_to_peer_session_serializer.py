import uuid
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers

from apps.core.utils.dailyco import DailyCoAPI
from apps.school.models import CourseEnrollment, LiveSession
from apps.users.models import StudentLead
from apps.school.serializers.livesession_serializer import DEFAULT_WHITEBOARD_LINK


class PeerLiveSessionSerializer(serializers.ModelSerializer):
    duration_hours = serializers.FloatField(write_only=True)
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "course",
            "teacher",
            "title",
            "description",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
            "started_at",
            "duration_hours", "ended_at",
        ]
        read_only_fields = [
            "id",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
            "started_at",
            "ended_at",
        ]

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
            enrolled = CourseEnrollment.objects.filter(
                student=user.student_profile, course=course, is_active=True
            ).exists()
            is_lead = StudentLead.objects.filter(
                student_profile=user.student_profile, course=course, is_a_lead=True
            ).exists()
            if not enrolled or not is_lead:
                lead_qs = StudentLead.objects.filter(
                    course=course, is_a_lead=True
                ).select_related("student_profile__user")
                lead_names = [
                    f"{lead.student_profile.user.first_name} {lead.student_profile.user.last_name}".strip()
                    for lead in lead_qs[:5]
                ]
                if not lead_names:
                    raise serializers.ValidationError(
                        "Only course leads can create live sessions. No lead is currently assigned for this course."
                    )
                raise serializers.ValidationError(
                    "Only course leads can create live sessions. "
                    f"Current lead(s): {', '.join(lead_names)}."
                )
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
