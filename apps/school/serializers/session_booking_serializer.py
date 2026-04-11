from rest_framework import serializers
from decimal import Decimal
from datetime import timedelta
from django.db import transaction
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
    teacher_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = SessionBooking
        fields = [
            "id", "teacher_id", "teacher_name", "scheduled_start", "duration_hours", "course",
            "course_title", "scheduled_end", "status", "is_allowed", "attended", "cost"
        ]
        read_only_fields = ["id", "is_allowed", "status", "attended", "cost", "scheduled_end", "teacher_name", "course_title"]

    def get_teacher_name(self, obj):
        """Return teacher full name"""
        if obj.teacher and obj.teacher.user:
            return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}"
        return ""

    def get_course_title(self, obj):
        """Return course title"""
        return obj.course.title if obj.course else ""

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        student_profile = None
        if not user.is_superuser:
            try:
                student_profile = StudentProfile.objects.get(user=user)
            except StudentProfile.DoesNotExist:
                raise serializers.ValidationError("Only students can create session bookings.")

        teacher_id = validated_data.pop("teacher_id")
        duration_hours = validated_data.pop("duration_hours")
        scheduled_start = validated_data.pop("scheduled_start")
        course = validated_data.pop("course")

        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
        except TeacherProfile.DoesNotExist:
            raise serializers.ValidationError("Invalid teacher selected.")

        if not teacher.hourly_rate:
            raise serializers.ValidationError("Teacher hourly rate not set.")
        
        teacher_rate = float(teacher.hourly_rate)
        total_cost = Decimal(duration_hours * teacher_rate)
        scheduled_end = scheduled_start + timedelta(hours=duration_hours)
        amount = Money(total_cost, "KES")

        if not user.is_superuser:
            try:
                student_wallet = user.wallet
            except Wallet.DoesNotExist:
                raise serializers.ValidationError("Student wallet not found.")

            if student_wallet.balance < amount:
                raise serializers.ValidationError("Insufficient balance to book this session.")

            system_wallet = Wallet.objects.filter(account_type="system").first()
            if not system_wallet:
                raise serializers.ValidationError("System wallet not found. Contact admin.")

            with transaction.atomic():
                student_wallet.balance -= amount
                student_wallet.save()

                system_wallet.balance += amount
                system_wallet.save()

                Transaction.objects.create(
                    wallet=student_wallet,
                    transaction_identifier=str(uuid.uuid4()),
                    amount=-amount.amount,
                    transaction_type="debit",
                    payment_method="wallet",
                    status="success",
                    description=f"Booking payment for teacher {teacher.user.get_full_name()}",
                    metadata_info={"session_booking": str(teacher.id)},
                )

                Transaction.objects.create(
                    wallet=system_wallet,
                    transaction_identifier=str(uuid.uuid4()),
                    amount=amount.amount,
                    transaction_type="credit",
                    payment_method="wallet",
                    status="success",
                    description=f"System hold for booking with student {user.username}",
                    metadata_info={"session_booking": str(teacher.id)},
                )

                booking = SessionBooking.objects.create(
                    student=student_profile,
                    teacher=teacher,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    cost=total_cost,
                    is_allowed=True,
                    course=course,
                    **validated_data,
                )
        else:
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
