import uuid
from typing import Optional, Dict, Any, Tuple
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.models import User, OnboardingStep
from apps.users.models import (
    StudentProfile,
    TeacherProfile,
    ParentProfile,
    ParentChild,
)
from apps.school.models import School, Grade, EducationLevel, Subject

STEP_ORDER = [
    OnboardingStep.PENDING_OTP,
    OnboardingStep.STEP_2_PROFILE,
    OnboardingStep.STEP_3_ACADEMIC_KYC,
    OnboardingStep.STEP_4_LAUNCH,
    OnboardingStep.COMPLETED,
]

STEP_NUMBERS = {
    OnboardingStep.PENDING_OTP: 1,
    OnboardingStep.STEP_2_PROFILE: 2,
    OnboardingStep.STEP_3_ACADEMIC_KYC: 3,
    OnboardingStep.STEP_4_LAUNCH: 4,
    OnboardingStep.COMPLETED: 4,
}


def get_step_number(step: Any) -> int:
    """Return numeric step (1..4) for a given onboarding state."""
    return STEP_NUMBERS.get(str(step), 1)


def get_resume_route(user: User) -> str:
    """Return canonical frontend resume URL matching SAD §7.6."""
    role = getattr(user, "role", None) or "student"
    step = str(getattr(user, "onboarding_step", OnboardingStep.PENDING_OTP))

    if step == OnboardingStep.COMPLETED:
        return f"/{role}-dashboard/home"

    step_number = get_step_number(step)
    return f"/onboarding/{role}?step={step_number}"


def assert_can_access_step(user: User, target_step: Any) -> None:
    """
    Enforce sequential step gating per SAD §8.1.
    Users cannot skip ahead before completing preceding phases.
    Users with 'completed' status may review or edit existing steps.
    """
    current_step = str(getattr(user, "onboarding_step", OnboardingStep.PENDING_OTP))
    if current_step == str(OnboardingStep.COMPLETED):
        return

    target_step_str = str(target_step)
    step_strings = [str(s) for s in STEP_ORDER]
    try:
        current_idx = step_strings.index(current_step)
        target_idx = step_strings.index(target_step_str)
    except ValueError:
        return

    if current_idx < target_idx:
        raise PermissionDenied(
            f"Please complete step {current_idx + 1} before proceeding to step {target_idx + 1}."
        )


@transaction.atomic
def associate_parent_child(
    parent_user: User, child_identifier: str
) -> Optional[ParentChild]:
    """
    Locates child by SBA student email, phone number, ID number, username, or UUID.
    Creates bidirectional link in ParentChild junction per SAD §8.4.
    """
    if not child_identifier:
        return None

    cleaned_identifier = str(child_identifier).strip()
    parent_profile, _ = ParentProfile.objects.get_or_create(user=parent_user)

    # 1. Search User table with role='student'
    student_user = (
        User.objects.filter(
            Q(email__iexact=cleaned_identifier)
            | Q(student_profile__parent_phone_number=cleaned_identifier)
            | Q(student_profile__guardian_contact=cleaned_identifier)
            | Q(student_profile__id_number=cleaned_identifier)
            | Q(username__iexact=cleaned_identifier),
            role="student",
        )
        .select_related("student_profile")
        .first()
    )

    student_profile = None
    if student_user and hasattr(student_user, "student_profile"):
        student_profile = student_user.student_profile
    else:
        # 2. Check if identifier is a UUID pointing directly to StudentProfile or User
        try:
            target_uuid = uuid.UUID(cleaned_identifier)
            student_profile = StudentProfile.objects.filter(
                Q(id=target_uuid) | Q(user__id=target_uuid)
            ).first()
        except (ValueError, TypeError):
            student_profile = None

    if not student_profile:
        return None

    link, _ = ParentChild.objects.get_or_create(
        parent=parent_profile,
        child=student_profile,
        defaults={"status": "active"},
    )
    return link


def get_user_draft_data(user: User) -> Dict[str, Any]:
    """Serialize current draft state for client hydration per SAD §7.6."""
    role = getattr(user, "role", None)
    draft: Dict[str, Any] = {}

    if role == "student":
        profile = getattr(user, "student_profile", None)
        if profile:
            draft = {
                "curriculum_type": profile.curriculum_type,
                "education_level_id": (
                    str(profile.education_level.id)
                    if profile.education_level
                    else None
                ),
                "education_level_name": (
                    profile.education_level.name
                    if profile.education_level
                    else None
                ),
                "grade_id": str(profile.grade.id) if profile.grade else None,
                "grade_name": profile.grade.level if profile.grade else None,
                "school_id": str(profile.school.id) if profile.school else None,
                "school_name": (
                    profile.school.name if profile.school else None
                ),
                "gender": profile.gender,
                "target_subjects": profile.target_subjects or [],
                "primary_learning_goal": profile.primary_learning_goal,
                "parent_phone_number": profile.parent_phone_number,
            }
    elif role == "teacher":
        profile = getattr(user, "teacher_profile", None)
        if profile:
            draft = {
                "national_identity_number": profile.national_identity_number,
                "tsc_number": profile.tsc_number or profile.teacher_license_number,
                "experience": profile.experience,
                "highest_qualification": profile.highest_qualification,
                "institution_attended": profile.institution_attended,
                "curriculums_taught": profile.curriculums_taught or [],
                "hourly_rate": (
                    float(profile.hourly_rate.amount)
                    if hasattr(profile.hourly_rate, "amount")
                    else (
                        float(profile.hourly_rate)
                        if profile.hourly_rate is not None
                        else 0.0
                    )
                ),
                "bio": profile.bio,
                "verification_status": profile.verification_status,
                "is_verified": profile.is_verified,
                "national_identity_card_url": (
                    profile.national_identity_card.url
                    if profile.national_identity_card
                    else None
                ),
                "academic_certificate_url": (
                    profile.academic_certificate.url
                    if profile.academic_certificate
                    else None
                ),
            }
    elif role == "parent":
        profile = getattr(user, "parent_profile", None)
        if profile:
            linked_children = []
            for pc in profile.parent_children.select_related(
                "child__user", "child__grade"
            ).all():
                child = pc.child
                linked_children.append(
                    {
                        "child_id": str(child.id),
                        "first_name": child.user.first_name,
                        "last_name": child.user.last_name,
                        "email": child.user.email,
                        "grade": child.grade.level if child.grade else None,
                        "status": pc.status,
                    }
                )
            draft = {
                "relationship_type": profile.relationship_type,
                "gender": profile.gender,
                "mpesa_billing_phone": profile.mpesa_billing_phone,
                "weekly_spend_limit_kes": (
                    float(profile.weekly_spend_limit_kes)
                    if profile.weekly_spend_limit_kes is not None
                    else 5000.00
                ),
                "notification_preferences": profile.notification_preferences or {},
                "linked_children": linked_children,
            }

    return draft
