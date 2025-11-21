import uuid
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from apps.school.models import CourseEnrollment
from apps.transactions.models import Transaction,Wallet
from apps.school.serializers.course_registration_serializer import(
    CourseNestedSerializer
)

class CourseEnrollmentSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField(read_only=True)
    course = CourseNestedSerializer(read_only=True)
    course_title = serializers.CharField(
        source="course.title", 
        read_only=True
    )
    amount_paid = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    description =serializers.CharField(
        source='course.description',
        read_only=True
    )
    
    
    class Meta:
        model = CourseEnrollment
        fields = [
            "id","course_title",'course',
            "student","purchased_at",
            "description","is_active",
            "transaction","amount_paid",
        ]
        read_only_fields = [
            "purchased_at","transaction",
            "is_active","amount_paid",
            "student",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        student = getattr(request.user, "student_profile", None)
        course = attrs.get("course")

        if not student:
            raise serializers.ValidationError(
                "Only students can enroll in courses."
            )

        if CourseEnrollment.objects.filter(course=course, student=student).exists():
            raise serializers.ValidationError("You are already enrolled in this course.")

        try:
            student_wallet = student.user.wallet
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Student wallet not found.")

        course_price = course.price
        if student_wallet.balance < course_price:
            raise serializers.ValidationError("Insufficient balance in your wallet.")

        attrs["student"] = student
        attrs["student_wallet"] = student_wallet
        attrs["course_price"] = course_price
        return attrs
    
    
    def create(self, validated_data):
        student = validated_data["student"]
        course = validated_data["course"]
        student_wallet = validated_data["student_wallet"]
        amount = validated_data["course_price"]  

        teacher = course.teacher
        if not teacher or not hasattr(teacher.user, "wallet"):
            raise serializers.ValidationError("Teacher or teacher wallet not found.")

        teacher_wallet = teacher.user.wallet

        with transaction.atomic():
            student_wallet.balance -= amount
            student_wallet.save()

            teacher_wallet.balance += amount
            teacher_wallet.save()

            Transaction.objects.create(
                wallet=student_wallet,
                transaction_identifier=str(uuid.uuid4()),
                amount=amount.amount, 
                transaction_type="debit",
                payment_method="wallet",
                status="success",
                description=f"Enrollment payment for course '{course.title}'",
                created_at=timezone.now(),
            )

            tx = Transaction.objects.create(
                wallet=teacher_wallet,
                transaction_identifier=str(uuid.uuid4()),
                amount=amount.amount, 
                transaction_type="credit",
                payment_method="wallet",
                status="success",
                description=f"Enrollment payment for course '{course.title}' by {student.user.username}",
                created_at=timezone.now(),
            )

            enrollment = CourseEnrollment.objects.create(
                course=course,
                student=student,
                transaction=tx,
                is_active=True,
                purchased_at=timezone.now(),
            )

        enrollment.amount_paid = amount.amount
        return enrollment
