import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import User, Core

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

    def __str__(self):
        return f"Parent: {self.user.first_name}"


class TeacherProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    tsc_number = models.CharField(
        max_length=50, 
        unique=True,
        null=True, 
        blank=True, 
        db_index=True,
    )
    academic_certificate = models.FileField()
    bio = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    subjects = models.ManyToManyField("school.Subject", related_name="teacher_profiles", blank=True)
    is_verified= models.BooleanField(default=False)
    grade =models.ManyToManyField('school.Grade', related_name='teacher_grades', blank=True, null=True)
    experience = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "teacher_profiles"
        ordering = ["user__first_name"]

    def __str__(self):
        return f"Teacher: {self.user.first_name}"


class StudentProfile(Core):
    """Represents a student's profile and academic relationships."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    contact_name = models.CharField(max_length=255, null=True, blank=True)
    guardian_contact = models.CharField(max_length=50, null=True, blank=True)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    subjects = models.ManyToManyField(
        'school.Subject',
        through="school.StudentSubject",  
        related_name="student_profiles",
    )

    bookings = models.ManyToManyField(
        'school.TutoringBooking',
        through="school.StudentBooking",  
        related_name="student_profiles",
        blank=True,
    )

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