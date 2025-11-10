# from rest_framework import serializers
# from django.utils import timezone
# from django.core.exceptions import ValidationError
# from apps.school.models import LiveSession, SessionBooking
# from apps.transactions.models import Transaction, Wallet
# from apps.core.utils.google_calendar import create_room
# from djmoney.money import Money
# import uuid

# class LiveSessionSerializer(serializers.ModelSerializer):
#     session_booking_id = serializers.UUIDField(write_only=True)

#     class Meta:
#         model = LiveSession
#         fields = [
#             "id",
#             "session_booking_id",
#             "meeting_link",
#             "started_at",
#             "ended_at",
#         ]
#         read_only_fields = ["id", "meeting_link", "started_at", "ended_at"]

#     def create(self, validated_data):
#         user = self.context["request"].user
#         session_booking_id = validated_data.pop("session_booking_id")

#         try:
#             booking = SessionBooking.objects.select_related("teacher", "student").get(id=session_booking_id)
#         except SessionBooking.DoesNotExist:
#             raise ValidationError("Invalid session booking.")

#         if not booking.is_allowed:
#             raise ValidationError("This booking is not allowed. Check wallet or approval status.")

#         if LiveSession.objects.filter(session=booking).exists():
#             raise ValidationError("A live session for this booking already exists.")

      
#         meet_link = create_daily_room_event(
#             teacher=booking.teacher,
#             summary=f"Session with {booking.teacher.user.first_name} {booking.teacher.user.last_name}",
#             start_time=booking.scheduled_start,
#             end_time=booking.scheduled_end,
#             description=f"Session for {booking.student.user.first_name} {booking.student.user.last_name}",
#             attendees_emails=[booking.student.user.email, booking.teacher.user.email],
#         )

#         live_session = LiveSession.objects.create(
#             session=booking,
#             teacher=booking.teacher,
#             meeting_link=meet_link,
#             started_at=timezone.now(),
#             ended_at=booking.scheduled_end
#         )

#         return live_session

    
#     def update(self, instance, validated_data):
#         """Mark session as attended and credit teacher."""
#         attended = booking.attended

#         if attended is True and not instance.attended:
#             instance.attended = True
#             instance.ended_at = timezone.now()
#             instance.save()

#             booking = instance.session_booking
#             teacher_wallet = Wallet.objects.get(user=booking.teacher.user)
#             amount = booking.cost

#             # Credit teacher
#             teacher_wallet.balance += amount
#             teacher_wallet.save()

#             # Log transaction
#             Transaction.objects.create(
#                 wallet=teacher_wallet,
#                 transaction_identifier=str(uuid.uuid4()),
#                 amount=amount,
#                 transaction_type="deposit",
#                 payment_method="wallet",
#                 status="success",
#                 description=f"Credit for attended session with {booking.student.user.get_full_name()}",
#                 metadata_info={"session_booking_id": str(booking.id)},
#             )

#         return instance