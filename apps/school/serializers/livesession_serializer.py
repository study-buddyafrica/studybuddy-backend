import uuid
from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.school.models import LiveSession, SessionBooking
from apps.transactions.models import Transaction, Wallet
from apps.core.utils.dailyco import DailyCoAPI


DEFAULT_WHITEBOARD_LINK = "https://miro.com/app/board/uXjVJs6oD7Q=/"

class LiveSessionSerializer(serializers.ModelSerializer):
    session_booking_id = serializers.UUIDField(write_only=True)
    teacher_meeting_link = serializers.CharField(read_only=True)
    student_meeting_link = serializers.CharField(read_only=True)
    whiteboard_link = serializers.URLField(read_only=True)

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "session_booking_id",
            "meeting_link",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
            "started_at",
            "ended_at",
            "title",
            "description",
        ]
        read_only_fields = [
            "id",
            "meeting_link",
            "teacher_meeting_link",
            "student_meeting_link",
            "whiteboard_link",
            "started_at",
            "ended_at",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        session_booking_id = validated_data.pop("session_booking_id")
        description = validated_data.get("description")
        title =validated_data.get("title")


        try:
            booking = SessionBooking.objects.select_related("teacher", "student").get(id=session_booking_id)
        except SessionBooking.DoesNotExist:
            raise ValidationError("Invalid session booking.")

        if not booking.is_allowed:
            raise ValidationError("This booking is not allowed. Check wallet or approval status.")

        if LiveSession.objects.filter(session=booking).exists():
            raise ValidationError("A live session for this booking already exists.")

        # ------------------- Daily.co Room ------------------- #
        daily_api = DailyCoAPI()
        random_suffix = uuid.uuid4().hex[:6]
        room_name = f"session_{booking.id.hex[:8]}_{random_suffix}"
        room = daily_api.create_room(
            name=room_name,
            end_time=booking.scheduled_end,
            properties={
                "enable_chat": True,
                "enable_screenshare": True,
                "start_audio_off": False,
                "start_video_off": False,
                "enable_prejoin_ui": True,
                "enable_people_ui": True,
                "enable_network_ui": True,
                "enable_pip_ui": True,
                "enable_emoji_reactions": True,
            }
        )

        teacher_token = daily_api.create_owner_token(
            room_name=room_name,
            user_id=str(booking.teacher.id),
            user_name=f"{booking.teacher.user.first_name} {booking.teacher.user.last_name}"
        )
        student_token = daily_api.create_participant_token(
            room_name=room_name,
            user_id=str(booking.student.id),
            user_name=f"{booking.student.user.first_name} {booking.student.user.last_name}"
        )

        live_session = LiveSession.objects.create(
            session=booking,
            teacher=booking.teacher,
            meeting_link=teacher_token["room_url"],
            whiteboard_link=DEFAULT_WHITEBOARD_LINK, 
            started_at=timezone.now(),
            ended_at=booking.scheduled_end,
            title=title,
            description=description
        )

        booking.status = "accepted"
        booking.teacher = booking.teacher
        booking.save(update_fields=["status", "teacher"])

        live_session.teacher_meeting_link = teacher_token["room_url"]
        live_session.student_meeting_link = student_token["room_url"]

        return live_session

    def update(self, instance, validated_data):
        instance.ended_at = timezone.now()
        instance.save(update_fields=["ended_at"])
        return instance