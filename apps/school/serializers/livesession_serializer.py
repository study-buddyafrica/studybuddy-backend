from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.school.models import LiveSession, SessionBooking
from apps.transactions.models import Transaction, Wallet
from apps.core.utils.dailyco import DailyCoAPI
import uuid


class LiveSessionSerializer(serializers.ModelSerializer):
    session_booking_id = serializers.UUIDField(write_only=True)
    teacher_meeting_link = serializers.CharField(read_only=True)
    student_meeting_link = serializers.CharField(read_only=True)

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "session_booking_id",
            "meeting_link",          
            "teacher_meeting_link",    
            "student_meeting_link",
            "started_at",
            "ended_at",
            "title",
            "description"
        ]
        read_only_fields = ["id", "meeting_link", "teacher_meeting_link", "student_meeting_link", "started_at", "ended_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        session_booking_id = validated_data.pop("session_booking_id")

        try:
            booking = SessionBooking.objects.select_related("teacher", "student").get(id=session_booking_id)
        except SessionBooking.DoesNotExist:
            raise ValidationError("Invalid session booking.")

        if not booking.is_allowed:
            raise ValidationError("This booking is not allowed. Check wallet or approval status.")

        if LiveSession.objects.filter(session=booking).exists():
            raise ValidationError("A live session for this booking already exists.")

        # Initialize DailyCo API
        daily_api = DailyCoAPI()

        room_name = f"session_{booking.id.hex[:8]}"
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

        # Generate tokens
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
            started_at=timezone.now(),
            ended_at=booking.scheduled_end
        )

        live_session.teacher_meeting_link = teacher_token["room_url"]
        live_session.student_meeting_link = student_token["room_url"]

        return live_session

    def update(self, instance, validated_data):
        """
        Mark session as attended and credit teacher.
        """
        booking = instance.session_booking

        if getattr(instance, "attended", False):
            return instance  # Already marked as attended

        attended = validated_data.get("attended", True)  # default to True if not provided

        if attended:
            instance.attended = True
            instance.ended_at = timezone.now()
            instance.save(update_fields=["attended", "ended_at"])

            # Credit teacher
            teacher_wallet = Wallet.objects.get(user=booking.teacher.user)
            amount = booking.cost
            teacher_wallet.balance += amount
            teacher_wallet.save(update_fields=["balance"])

            # Log transaction
            Transaction.objects.create(
                wallet=teacher_wallet,
                transaction_identifier=str(uuid.uuid4()),
                amount=amount,
                transaction_type="deposit",
                payment_method="wallet",
                status="success",
                description=f"Credit for attended session with {booking.student.user.get_full_name()}",
                metadata_info={"session_booking_id": str(booking.id)},
            )

        return instance
