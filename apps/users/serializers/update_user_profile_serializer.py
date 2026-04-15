from rest_framework import serializers
from apps.users.models import TeacherProfile, StudentProfile, ParentProfile
from apps.transactions.models import Wallet
from apps.core.validators import (
    validate_birth_date_teacher,
    validate_phone_number,
    validate_hourly_rate,
    validate_string_length,
)
from apps.core.serializers.sanitize_mixin import SanitizeHTMLMixin


class TeacherProfileUpdateSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["bio"]

    class Meta:
        model = TeacherProfile
        fields = [
            "bio",
            "phone",
            "hourly_rate",
            "subjects",
            "grade",
            "education_level",
            "experience",
            "profile_picture",
            "teacher_license_number",
            "teacher_license_certificate",
            "academic_certificate",
            "cv",
            "birth_date",
            "gender",
            "school",
            "national_identity_number",
            "national_identity_card",
        ]
        read_only_fields = ["id", "user", "is_verified"]

    def validate_birth_date(self, value):
        """Validate teacher birth date (must be 18+)"""
        validate_birth_date_teacher(value)
        return value

    def validate_phone(self, value):
        """Validate phone number format"""
        if value:
            validate_phone_number(value)
            validate_string_length(
                value, min_length=10, max_length=20, field_name="Phone"
            )
        return value

    def validate_hourly_rate(self, value):
        """Validate hourly rate"""
        if value:
            validate_hourly_rate(value)
        return value

    def validate_bio(self, value):
        """Validate bio length"""
        if value:
            validate_string_length(
                value, min_length=10, max_length=1000, field_name="Bio"
            )
        return value

    def update(self, instance, validated_data):
        subjects = validated_data.pop("subjects", None)
        grades = validated_data.pop("grade", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if subjects is not None:
            instance.subjects.set(subjects)

        if grades is not None:
            instance.grade.set(grades)

        instance.save()
        return instance


class StudentProfileUpdateSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["contact_name"]

    class Meta:
        model = StudentProfile
        fields = [
            "profile_picture",
            "birth_date",
            "contact_name",
            "guardian_contact",
            "grade",
            "education_level",
            "school",
        ]
        read_only_fields = ["id", "user", "enrollment_date"]

    def validate_birth_date(self, value):
        """Validate student birth date (can be any age but not future)"""
        from apps.core.validators import validate_birth_date_student

        validate_birth_date_student(value)
        return value

    def validate_contact_name(self, value):
        """Validate contact name length"""
        if value:
            validate_string_length(
                value, min_length=2, max_length=255, field_name="Contact name"
            )
        return value

    def validate_guardian_contact(self, value):
        """Validate guardian contact"""
        if value:
            validate_phone_number(value)
            validate_string_length(
                value, min_length=10, max_length=20, field_name="Guardian contact"
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["grade_id"] = data.get("grade")
        data["school_id"] = data.get("school")
        data["education_level_id"] = data.get("education_level")
        data["education_level_name"] = (
            instance.education_level.name if instance.education_level else None
        )
        data["grade"] = instance.grade.level if instance.grade else None
        data["school"] = instance.school.name if instance.school else None
        return data


class ParentProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ParentProfile
        fields = [
            "profile_picture",
            "birth_date",
            "full_name",
        ]
        read_only_fields = ["id", "user", "children", "full_name"]

    def validate_birth_date(self, value):
        """Validate parent birth date (must be 18+)"""
        from apps.core.validators import validate_birth_date_parent

        validate_birth_date_parent(value)
        return value

    def get_full_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class ParentChildSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    school = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = ["id", "full_name", "grade", "school", "birth_date"]

    def get_full_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_grade(self, obj) -> str | None:
        return obj.grade.level if obj.grade else None

    def get_school(self, obj) -> str | None:
        return obj.school.name if obj.school else None


class ParentFullProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    children = ParentChildSummarySerializer(many=True, read_only=True)
    wallet_balance = serializers.SerializerMethodField()
    wallet_currency = serializers.SerializerMethodField()
    wallet_account_type = serializers.SerializerMethodField()

    class Meta:
        model = ParentProfile
        fields = [
            "id",
            "full_name",
            "email",
            "profile_picture",
            "birth_date",
            "gender",
            "national_identity_number",
            "children",
            "wallet_balance",
            "wallet_currency",
            "wallet_account_type",
        ]

    def get_full_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_wallet_balance(self, obj) -> str | None:
        wallet = Wallet.objects.filter(user=obj.user).first()
        return str(wallet.balance) if wallet else None

    def get_wallet_currency(self, obj) -> str | None:
        wallet = Wallet.objects.filter(user=obj.user).first()
        return wallet.balance_currency if wallet else None

    def get_wallet_account_type(self, obj) -> str | None:
        wallet = Wallet.objects.filter(user=obj.user).first()
        return wallet.account_type if wallet else None
