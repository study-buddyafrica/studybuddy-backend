import uuid
import os
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import User, Core

def certificate_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("certificates", new_filename)


def validate_pdf(value):
    if not value.name.lower().endswith('.pdf'):
        raise ValidationError("Only PDF files are allowed.")
    if value.size > 10 * 1024 * 1024:  
        raise ValidationError("File too large ( >5MB ).")

class ParentChild(Core):
    parent = models.ForeignKey(
        'ParentProfile',
        on_delete=models.CASCADE,
        related_name="parent_children"
    )
    child = models.ForeignKey(
        'StudentProfile',
        on_delete=models.CASCADE,
        related_name="child_parents"
    )

    class Meta:
        db_table = "parent_children"
        unique_together = ("parent", "child")

    def __str__(self):
        return f"{self.parent.user.first_name} → {self.child.user.first_name}"


class ParentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="parent_profile"
    )
    children = models.ManyToManyField(
        'StudentProfile',
        through=ParentChild,
        related_name="parent_profiles"
    )
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    national_identity_number = models.CharField(
        max_length=15, 
        null=True, 
        blank=True,
        help_text="National Identity Number",
    )
    national_identity_card = models.FileField(
        upload_to="identity_cards/",
        null=True, blank=True,
        help_text = "National Identity card "
    )

    def __str__(self):
        return f"Parent: {self.user.first_name}"


class TeacherProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ("ongoing", "Ongoing"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    is_verified= models.BooleanField(default=False)
    experience = models.PositiveSmallIntegerField(default=0)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    teacher_license_number = models.CharField(
        max_length=50, 
        unique=True,
        null=True, 
        blank=True, 
        db_index=True,
    )
    teacher_license_certificate = models.FileField(
        upload_to=certificate_upload_path,
        validators=[validate_pdf], 
        null=True, blank=True
    )
    academic_certificate = models.FileField(
        upload_to=certificate_upload_path,
        validators=[validate_pdf], 
        null=True, blank=True
    )
    bio = models.TextField(
        null=True, blank=True
    )
    phone = models.CharField(
        max_length=50, 
        null=True, blank=True
    )
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    grade =models.ManyToManyField(
        'school.Grade', 
        related_name='teacher_grades', 
        blank=True, null=True
    )
    profile_picture = models.ImageField(
        upload_to="profiles/", 
        null=True, blank=True
    )
    birth_date = models.DateField(
        null=True, blank=True
    )
    google_access_token = models.TextField(
        null=True, 
        blank=True
    )
    google_refresh_token = models.TextField(
        null=True, 
        blank=True
    )
    google_token_expiry = models.DateTimeField(
        null=True, 
        blank=True
    )
    gender = models.CharField(
        max_length=50, 
        null=True, 
        blank=True
    )
    national_identity_number = models.CharField(
        max_length=15, 
        null=True, 
        blank=True,
        help_text="National Identity Number",
    )
    national_identity_card = models.FileField(
        upload_to="identity_cards/",
        null=True, blank=True
    )
    cv = models.FileField(
        upload_to="cvs/", 
        null=True, blank=True
    )
    subjects = models.ManyToManyField(
        "school.Subject",
        related_name="teacher_profiles" 
    )
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='ongoing',
    )
    school = models.ForeignKey(
        "school.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachers",
    )

    class Meta:
        db_table = "teacher_profiles"
        ordering = ["user__first_name"]

    def __str__(self):
        return f"Teacher: {self.user.first_name}"


class StudentProfile(Core):
    """Represents a student's profile and academic relationships."""
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )
    grade = models.ForeignKey(
        'school.Grade',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
        db_index=True,
    )
    school = models.ForeignKey(
        'school.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    guardian_contact = models.CharField(max_length=50, null=True, blank=True)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    id_number = models.CharField(max_length=15, null=True, blank=True)
    parents = models.ManyToManyField(
        'ParentProfile',
        through=ParentChild,
        related_name="student_profiles",
    )

    class Meta:
        db_table = "student_profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["grade"]),
            models.Index(fields=["school"]),
        ]

    def __str__(self):
        return f"{self.user.first_name or 'Student'} ({self.user.email})"


class Availability(models.Model):
    """Teacher recurring availability or single slots"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name="availability",
    )
    date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    is_blocked = models.BooleanField(default=False)

    class Meta:
        db_table = "availability"
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["is_blocked"]),
        ]

    def __str__(self):
        return f"{self.teacher} — {self.date:%Y-%m-%d %H:%M}"


class TeacherRating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="teacher_ratings",
    )
    rating = models.PositiveSmallIntegerField()  # 1–5 stars
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "teacher_ratings"
        unique_together = ("teacher", "student")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["rating"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.teacher} rated {self.rating}/5 by {self.student}"


class StudentLead(Core):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    course = models.ForeignKey(
        "school.Course",
        on_delete=models.CASCADE,
        related_name="student_leads",
    )
    student_profile = models.ForeignKey(
            StudentProfile,
            on_delete=models.CASCADE,
            related_name="leads",
    )
    is_a_lead = models.BooleanField(default=False)

    class Meta:
        db_table ='student_leads'
        unique_together = ("course", "student_profile")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.student_profile.user.first_name} is a lead {self.is_a_lead}"
