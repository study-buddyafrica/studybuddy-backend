from rest_framework import serializers
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta

from apps.school.models import SessionBooking
from apps.users.models import TeacherProfile, StudentProfile


class SessionBookingSerializer(serializers.ModelSerializer):
    teacher_id = serializers.UUIDField(write_only=True)
    scheduled_start = serializers.DateTimeField()
    duration_hours = serializers.FloatField(write_only=True)
    scheduled_end = serializers.DateTimeField(read_only=True)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = SessionBooking
        fields = [
            "id", "teacher_id", "scheduled_start", "duration_hours",
            "scheduled_end", "status", "is_allowed", "attended", "cost"
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
        duration_hours = validated_data.pop("duration_hours")

        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
        except TeacherProfile.DoesNotExist:
            raise ValidationError("Invalid teacher selected.")

        if not teacher.hourly_rate:
            raise ValidationError("Teacher hourly rate not set.")

        student_wallet = getattr(user, "wallet", None)
        if not student_wallet:
            raise ValidationError("Student wallet not found.")

        teacher_rate = float(teacher.hourly_rate)
        balance = float(student_wallet.balance.amount)
        max_affordable_hours = balance / teacher_rate
        if max_affordable_hours < 1:
            raise ValidationError("Wallet balance cannot afford even 1 hour of session time.")

        if duration_hours <= 0:
            raise ValidationError("Duration must be greater than 0 hours.")

        if duration_hours > max_affordable_hours:
            raise ValidationError(
                f"Insufficient balance. You can book up to {max_affordable_hours:.2f} hours."
            )

        total_cost = Decimal(duration_hours * teacher_rate)
        scheduled_start = validated_data.pop("scheduled_start")
        scheduled_end = scheduled_start + timedelta(hours=duration_hours)

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