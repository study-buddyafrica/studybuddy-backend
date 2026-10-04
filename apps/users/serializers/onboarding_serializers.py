import uuid
from typing import Any, Dict, List, Optional
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.models import User, OnboardingStep
from apps.core.validators import validate_kyc_document
from apps.users.models import (
    StudentProfile,
    TeacherProfile,
    ParentProfile,
    ParentChild,
)
from apps.school.models import School, Grade, EducationLevel, Subject
from apps.users.services.onboarding_service import (
    assert_can_access_step,
    associate_parent_child,
    get_step_number,
    get_resume_route,
    get_user_draft_data,
)


class OnboardingStep2Serializer(serializers.Serializer):
    """
    Step 2 Serializer handling Student academic tier,
    Teacher KYC national identity, and Parent learner linkage.
    """

    # Student fields
    curriculum_type = serializers.ChoiceField(
        choices=["CBC", "8_4_4", "IGCSE", "OTHER"], required=False
    )
    education_level_id = serializers.UUIDField(required=False, allow_null=True)
    grade_id = serializers.UUIDField(required=False, allow_null=True)
    school_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    school_id = serializers.UUIDField(required=False, allow_null=True)
    gender = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )

    # Teacher fields
    national_identity_number = serializers.CharField(
        max_length=30, required=False, allow_blank=True
    )
    tsc_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    experience = serializers.IntegerField(
        min_value=0, max_value=50, required=False
    )
    national_identity_card = serializers.FileField(
        required=False, allow_null=True, validators=[validate_kyc_document]
    )
    bio = serializers.CharField(
        required=False, allow_blank=True
    )

    # Parent fields
    relationship_type = serializers.ChoiceField(
        choices=["Father", "Mother", "Guardian", "Sponsor"], required=False
    )
    child_identifier = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    child_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_education_level_id(self, value):
        if value and not EducationLevel.objects.filter(id=value).exists():
            raise ValidationError("Invalid education level ID.")
        return value

    def validate_grade_id(self, value):
        if value and not Grade.objects.filter(id=value).exists():
            raise ValidationError("Invalid grade ID.")
        return value

    def validate_school_id(self, value):
        if value and not School.objects.filter(id=value).exists():
            raise ValidationError("Invalid school ID.")
        return value

    @transaction.atomic
    def save(self, **kwargs):
        user: User = self.context["request"].user
        role = getattr(user, "role", None) or "student"
        data = self.validated_data

        if role == "student":
            profile, _ = StudentProfile.objects.get_or_create(user=user)

            if "curriculum_type" in data:
                profile.curriculum_type = data["curriculum_type"]

            if "education_level_id" in data:
                profile.education_level = (
                    EducationLevel.objects.filter(
                        id=data["education_level_id"]
                    ).first()
                    if data["education_level_id"]
                    else None
                )

            if "grade_id" in data:
                profile.grade = (
                    Grade.objects.filter(id=data["grade_id"]).first()
                    if data["grade_id"]
                    else None
                )

            if "school_id" in data and data["school_id"]:
                profile.school = School.objects.filter(
                    id=data["school_id"]
                ).first()
            elif "school_name" in data and data["school_name"]:
                school_name = data["school_name"].strip()
                school, _ = School.objects.get_or_create(
                    name=school_name,
                    defaults={
                        "address": school_name,
                        "city": "Nairobi",
                        "contact": "",
                        "is_approved": False,
                    },
                )
                profile.school = school

            if "gender" in data and data["gender"]:
                profile.gender = data["gender"]

            profile.save()

        elif role == "teacher":
            profile, _ = TeacherProfile.objects.get_or_create(user=user)

            if "national_identity_number" in data:
                profile.national_identity_number = data[
                    "national_identity_number"
                ]

            if "tsc_number" in data and data["tsc_number"]:
                tsc = data["tsc_number"].strip()
                profile.tsc_number = tsc
                if not profile.teacher_license_number:
                    profile.teacher_license_number = tsc

            if "experience" in data:
                profile.experience = data["experience"]

            if "national_identity_card" in data and data["national_identity_card"]:
                profile.national_identity_card = data["national_identity_card"]

            if "bio" in data and data["bio"]:
                profile.bio = data["bio"]

            if "gender" in data and data["gender"]:
                profile.gender = data["gender"]

            profile.save()

        elif role == "parent":
            profile, _ = ParentProfile.objects.get_or_create(user=user)

            if "relationship_type" in data:
                profile.relationship_type = data["relationship_type"]

            if "gender" in data and data["gender"]:
                profile.gender = data["gender"]

            profile.save()

            # Process ward association
            child_target = data.get("child_id") or data.get("child_identifier")
            if child_target:
                associate_parent_child(user, str(child_target))

        # Advance state to Step 3 if currently at Step 2 or pending_otp
        if user.onboarding_step in [
            OnboardingStep.PENDING_OTP,
            OnboardingStep.STEP_2_PROFILE,
        ]:
            user.onboarding_step = OnboardingStep.STEP_3_ACADEMIC_KYC
            user.save(update_fields=["onboarding_step"])

        return {
            "current_step": 2,
            "next_step": 3,
            "onboarding_step": user.onboarding_step,
        }


class OnboardingStep3Serializer(serializers.Serializer):
    """
    Step 3 Serializer handling Student goals & parent phone,
    Teacher qualifications, certificates, rates & subjects,
    and Parent M-Pesa billing preferences.
    """

    # Student fields
    target_subjects = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    primary_learning_goal = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    parent_phone_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )

    # Teacher fields
    highest_qualification = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    institution_attended = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    curriculums_taught = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
    )
    hourly_rate_kes = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal("0.00")
    )
    hourly_rate = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal("0.00")
    )
    bio = serializers.CharField(required=False, allow_blank=True)
    academic_certificate = serializers.FileField(
        required=False, allow_null=True, validators=[validate_kyc_document]
    )
    subjects = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )

    # Parent fields
    mpesa_billing_phone = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    weekly_spend_limit_kes = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal("0.00")
    )
    notification_preferences = serializers.DictField(required=False)

    @transaction.atomic
    def save(self, **kwargs):
        from djmoney.money import Money

        user: User = self.context["request"].user
        role = getattr(user, "role", None) or "student"
        data = self.validated_data

        if role == "student":
            profile, _ = StudentProfile.objects.get_or_create(user=user)

            if "target_subjects" in data:
                profile.target_subjects = data["target_subjects"]

            if "primary_learning_goal" in data:
                profile.primary_learning_goal = data["primary_learning_goal"]

            if "parent_phone_number" in data:
                profile.parent_phone_number = data["parent_phone_number"]
                if not profile.guardian_contact:
                    profile.guardian_contact = data["parent_phone_number"]

            profile.save()

        elif role == "teacher":
            profile, _ = TeacherProfile.objects.get_or_create(user=user)

            if "highest_qualification" in data:
                profile.highest_qualification = data["highest_qualification"]

            if "institution_attended" in data:
                profile.institution_attended = data["institution_attended"]

            if "curriculums_taught" in data:
                profile.curriculums_taught = data["curriculums_taught"]

            rate = data.get("hourly_rate_kes") or data.get("hourly_rate")
            if rate is not None:
                profile.hourly_rate = Money(rate, "KES")

            if "bio" in data and data["bio"]:
                profile.bio = data["bio"]

            if "academic_certificate" in data and data["academic_certificate"]:
                profile.academic_certificate = data["academic_certificate"]

            if "subjects" in data and data["subjects"]:
                subject_objs = []
                for sub_item in data["subjects"]:
                    sub_str = str(sub_item).strip()
                    try:
                        sub_uuid = uuid.UUID(sub_str)
                        sub_inst = Subject.objects.filter(id=sub_uuid).first()
                    except (ValueError, TypeError):
                        sub_inst, _ = Subject.objects.get_or_create(name=sub_str)
                    if sub_inst:
                        subject_objs.append(sub_inst)
                if subject_objs:
                    profile.subjects.set(subject_objs)

            profile.verification_status = "ongoing"
            profile.is_verified = False
            profile.save()

        elif role == "parent":
            profile, _ = ParentProfile.objects.get_or_create(user=user)

            if "mpesa_billing_phone" in data:
                profile.mpesa_billing_phone = data["mpesa_billing_phone"]

            if "weekly_spend_limit_kes" in data:
                profile.weekly_spend_limit_kes = data["weekly_spend_limit_kes"]

            if "notification_preferences" in data:
                profile.notification_preferences = data["notification_preferences"]

            profile.save()

        # Advance state to Step 4 Launch if currently at Step 3
        if user.onboarding_step == OnboardingStep.STEP_3_ACADEMIC_KYC:
            user.onboarding_step = OnboardingStep.STEP_4_LAUNCH
            user.save(update_fields=["onboarding_step"])

        return {
            "current_step": 3,
            "next_step": 4,
            "onboarding_step": user.onboarding_step,
        }
