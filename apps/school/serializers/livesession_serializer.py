from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.school.models import LiveSession, SessionBooking
from apps.transactions.models import Transaction, Wallet
from apps.core.utils.google_calendar import generate_google_meet_link
from djmoney.money import Money
import uuid

class LiveSessionSerializer(serializers.ModelSerializer):
    session_booking_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "session_booking_id",
            "meeting_link",
            "started_at",
            "ended_at",
        ]
        read_only_fields = ["id", "meeting_link", "started_at", "ended_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        session_booking_id = validated_data.pop("session_booking_id")

        try:
            booking = SessionBooking.objects.select_related("teacher", "student").get(id=session_booking_id)
        except SessionBooking.DoesNotExist:
            raise ValidationError("Invalid session booking.")

        if not booking.is_allowed:
            raise ValidationError("This booking is not allowed. Check wallet or approval status.")

        if booking.student.user != user:
            raise ValidationError("You can only start your own sessions.")
        
        if LiveSession.objects.filter(session_booking=booking).exists():
            raise ValidationError("A live session for this booking already exists.")

        meet_link = generate_google_meet_link(
            summary=f"Session with {booking.teacher.user.get_full_name()}",
            start_time=booking.scheduled_start,
            end_time=booking.scheduled_end,
            attendees=[
                booking.student.user.email,
                booking.teacher.user.email,
            ]
        )

        live_session = LiveSession.objects.create(
            session_booking=booking,
            meeting_link=meet_link,
            started_at=timezone.now(),
        )

        return live_session

    def update(self, instance, validated_data):
        """Mark session as attended and credit teacher."""
        attended = validated_data.get("attended", None)

        if attended is True and not instance.attended:
            instance.attended = True
            instance.ended_at = timezone.now()
            instance.save()

            booking = instance.session_booking
            teacher_wallet = Wallet.objects.get(user=booking.teacher.user)
            amount = booking.cost

            teacher_wallet.balance += amount
            teacher_wallet.save()

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
