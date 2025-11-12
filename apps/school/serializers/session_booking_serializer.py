from rest_framework import serializers
from decimal import Decimal
from datetime import timedelta
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from djmoney.money import Money
import uuid

from apps.school.models import SessionBooking
from apps.users.models import TeacherProfile, StudentProfile
from apps.transactions.models import Wallet, Transaction


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

    def _log_transaction(self, wallet, amount, tx_type, description, related_tx=None):
        """Helper to create a transaction log."""
        return Transaction.objects.create(
            wallet=wallet,
            transaction_identifier=str(uuid.uuid4()),
            amount=amount.amount if isinstance(amount, Money) else amount,
            transaction_type=tx_type,
            payment_method="wallet",
            status="success",
            description=description,
            related_transaction=related_tx,
            metadata_info={
                "timestamp": str(timezone.now()),
                "initiated_by": wallet.user.email if wallet.user else "system",
            },
        )

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        # Only enforce student profile for normal users
        if not user.is_superuser:
            try:
                student_profile = StudentProfile.objects.get(user=user)
            except StudentProfile.DoesNotExist:
                raise ValidationError("Only students can create session bookings.")
        else:
            student_profile = None

        teacher_id = validated_data.pop("teacher_id")
        duration_hours = validated_data.pop("duration_hours")

        # Ensure teacher exists
        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
        except TeacherProfile.DoesNotExist:
            raise ValidationError("Invalid teacher selected.")

        if not teacher.hourly_rate:
            raise ValidationError("Teacher hourly rate not set.")

        # Student wallet
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
        amount = Money(total_cost, "KES")

        # Deduct student wallet
        if not student_wallet.can_make_transaction(amount):
            raise ValidationError("Insufficient balance to complete booking.")
        student_wallet.withdraw(amount)
        student_tx = self._log_transaction(
            student_wallet, amount, "debit", f"Payment for session booking with teacher {teacher.user.username}"
        )

        # Deposit into system wallet (assumes system wallet exists)
        try:
            system_wallet = Wallet.objects.get(account_type="system")
        except Wallet.DoesNotExist:
            raise ValidationError("System wallet not found. Please create it in admin.")

        system_wallet.deposit(amount)
        self._log_transaction(
            system_wallet, amount, "credit", f"System holds payment for student booking with teacher {teacher.user.username}",
            related_tx=student_tx
        )

        # Create session booking
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

    def update(self, instance, validated_data):
        """Prevent update if within 30 minutes of session start."""
        now = timezone.now()
        if instance.scheduled_start - now <= timedelta(minutes=30):
            raise ValidationError("You cannot update this booking within 30 minutes of start time.")

        validated_data.pop("teacher_id", None)
        validated_data.pop("duration_hours", None)

        return super().update(instance, validated_data)
