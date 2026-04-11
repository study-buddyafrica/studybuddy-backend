from rest_framework import serializers
from apps.users.models import TeacherProfile, StudentProfile, ParentProfile
from apps.core.validators import (
    validate_birth_date_teacher,
    validate_phone_number,
    validate_hourly_rate,
    validate_string_length,
)


class TeacherProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = [
            "bio",
            "phone",
            "hourly_rate",
            "subjects",
            "grade",
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


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            "profile_picture",
            "birth_date",
            "contact_name",
            "guardian_contact",
            "grade",
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

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
