from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from apps.school.models import SessionBooking
from apps.users.models import TeacherProfile, StudentProfile
from apps.transactions.models import Wallet

class SessionBookingSerializer(serializers.ModelSerializer):
    teacher_id = serializers.UUIDField(write_only=True)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField(read_only=True)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = SessionBooking
        fields = [
            "id", "teacher_id", "scheduled_start", "scheduled_end",
            "status", "is_allowed", "attended", "cost"
        ]
        read_only_fields = ["id", "is_allowed", "status", "attended", "cost", "scheduled_end"]

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        try:
            student_profile = StudentProfile.objects.get(user=user)
        except StudentProfile.DoesNotExist:
            raise ValidationError("Only students can create session bookings.")

        teacher_id = validated_data.pop("teacher_id")
        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
        except TeacherProfile.DoesNotExist:
            raise ValidationError("Invalid teacher selected.")

        student_wallet = getattr(user, "wallet", None)
        teacher_rate = teacher.hourly_rate.amount if teacher.hourly_rate else 0

        if not student_wallet:
            raise ValidationError("Student wallet not found.")

        if student_wallet.balance.amount < teacher_rate:
            raise ValidationError(
                f"Insufficient balance. Required at least: {teacher_rate} KES."
            )

        scheduled_start = validated_data["scheduled_start"]

        affordable_hours = int(student_wallet.balance.amount // teacher_rate)
        if affordable_hours < 1:
            raise ValidationError("Wallet balance cannot afford even 1 hour of session time.")

        scheduled_end = scheduled_start + timedelta(hours=affordable_hours)
        total_cost = teacher_rate * affordable_hours

        with transaction.atomic():
            student_wallet.balance.amount -= total_cost
            student_wallet.save()

            booking = SessionBooking.objects.create(
                student=student_profile,
                teacher=teacher,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                cost=total_cost,
                is_allowed=True,
                **validated_data,
            )

        return booking
