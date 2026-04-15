"""Global pre-save sanitization for user-generated text fields."""

import bleach
from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.school.models import Course, Topic, Subtopic, Subject, LiveSession, RevisionMaterial, Assessment, Question, Choice
from apps.users.models import TeacherProfile, StudentProfile

MODEL_TEXT_FIELDS = {
    Course: ["title", "description"],
    Topic: ["title", "description"],
    Subtopic: ["title", "content"],
    Subject: ["name", "description"],
    LiveSession: ["title", "description"],
    RevisionMaterial: ["title", "description"],
    Assessment: ["title", "description"],
    Question: ["text"],
    Choice: ["text"],
    TeacherProfile: ["bio"],
    StudentProfile: ["contact_name"],
}


def _clean_text(value: str) -> str:
    """Strip all HTML/script content before persisting text fields."""
    return bleach.clean(
        value,
        tags=[],
        attributes={},
        strip=True,
        strip_comments=True,
    )


@receiver(pre_save)
def sanitize_user_generated_text(sender, instance, **kwargs):
    fields = MODEL_TEXT_FIELDS.get(sender)
    if not fields:
        return

    for field_name in fields:
        current = getattr(instance, field_name, None)
        if isinstance(current, str) and current:
            cleaned = _clean_text(current)
            if cleaned != current:
                setattr(instance, field_name, cleaned)
