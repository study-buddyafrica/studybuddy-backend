from django.db import models
from apps.core.models import Core
import uuid
from django.utils import timezone

class School(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    contact = models.CharField(max_length=50)
    is_approved = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_schools"
    )

    class Meta:
        db_table = "schools"
        ordering = ["name"]
    
    def __str__(self):
        return self.name

class Grade(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        db_table = "grades"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}"


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"

class Subject(Core):
    """Represents a subject taught in a specific class (e.g., Mathematics, Biology)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True, null=True, blank=True)
    name = models.CharField(max_length=150, db_index=True)
    description = models.TextField(blank=True, null=True)
    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, related_name="subjects"
    )

   
    teachers = models.ManyToManyField(
        'users.TeacherProfile',
        through="TeacherSubject",
        related_name="school_subjects",
    )
    students = models.ManyToManyField(
        'users.StudentProfile',
        through="StudentSubject",  
        related_name="school_subjects",
    )

    def __str__(self):
        return f"{self.name} ({self.code or 'N/A'})"

    class Meta:
        db_table = "subjects"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["code"]),
        ]

class TeacherSubject(models.Model):
    """Intermediate table for many-to-many between Teacher and Subject."""
    id = models.BigAutoField(primary_key=True)
    teacher = models.ForeignKey(
        'users.TeacherProfile',  
        on_delete=models.CASCADE,
        related_name="teacher_subject_links",
    )
    subject = models.ForeignKey(
        "Subject",
        on_delete=models.CASCADE,
        related_name="teacher_subject_links",
    )

    class Meta:
        db_table = "teacher_subjects"
        unique_together = ("teacher", "subject")
        indexes = [
            models.Index(fields=["teacher"]),
            models.Index(fields=["subject"]),
        ]

    def __str__(self):
        return f"{self.teacher.user.first_name} - {self.subject.name}"

class StudentSubject(models.Model):
    """Intermediate table for many-to-many between Student and Subject."""
    id = models.BigAutoField(primary_key=True)
    student = models.ForeignKey(
        'users.StudentProfile',
        on_delete=models.CASCADE,
        related_name="student_subject_links",
    )
    subject = models.ForeignKey(
        "Subject",
        on_delete=models.CASCADE,
        related_name="student_subject_links",
    )

    class Meta:
        db_table = "student_subjects"
        unique_together = ("student", "subject")
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["subject"]),
        ]

    def __str__(self):
        return f"{self.student.user.first_name} - {self.subject.name}"


class StudentBooking(models.Model):
    """Through model for Student-Booking relationship"""
    id = models.BigAutoField(primary_key=True)
    student = models.ForeignKey(
        'users.StudentProfile',
        on_delete=models.CASCADE,
        related_name="student_booking_links",
    )
    booking = models.ForeignKey(
        'TutoringBooking',
        on_delete=models.CASCADE,
        related_name="student_booking_links",
    )
    
    class Meta:
        db_table = "student_bookings"
        unique_together = ("student", "booking")
        
    def __str__(self):
        return f"{self.student} - {self.booking}"


class Topic(Core):
    """High-level topic under a specific subject."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "topics"
        ordering = ["subject", "order"]
        indexes = [
            models.Index(fields=["subject"]),
        ]

    def __str__(self):
        return f"{self.subject.name}: {self.title}"


class Subtopic(Core):
    """Subtopic or lesson content under a topic."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="subtopics",
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    

    class Meta:
        db_table = "subtopics"
        ordering = ["topic", "order"]
        indexes = [
            models.Index(fields=["topic"]),
        ]

    def __str__(self):
        return f"{self.topic.title} → {self.title}"


class LiveSession(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    meeting_link = models.URLField(max_length=500, null=True, blank=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity = models.PositiveIntegerField(default=0)

    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name="live_sessions"
    )
    teacher = models.ForeignKey(
        'users.TeacherProfile', on_delete=models.CASCADE, related_name="live_sessions"  
    )

    class Meta:
        db_table = "live_sessions"
        ordering = ["-scheduled_start"]

    def __str__(self):
        return f"{self.title} ({self.scheduled_start:%Y-%m-%d})"


class SessionBooking(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    live_session = models.ForeignKey(
        LiveSession, on_delete=models.CASCADE, related_name="bookings"
    )
    student = models.ForeignKey(
        'users.StudentProfile', on_delete=models.CASCADE, related_name="session_bookings" 
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )
    
    attended = models.BooleanField(default=False)

    class Meta:
        db_table = "session_bookings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Booking: {self.student} → {self.live_session} ({self.status})"


class TutoringBooking(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        'users.TeacherProfile', on_delete=models.CASCADE, related_name="tutoring_bookings" 
    )
    student = models.ForeignKey(
        'users.StudentProfile', on_delete=models.CASCADE, related_name="tutoring_bookings"  
    )
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )
    

    class Meta:
        db_table = "tutoring_bookings"
        ordering = ["-start_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["start_at"]),
        ]

    def __str__(self):
        return f"Tutoring: {self.student} ↔ {self.teacher} ({self.status})"


class RevisionMaterial(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    file_url = models.URLField(max_length=1000)
    uploaded_by = models.ForeignKey('users.TeacherProfile', on_delete=models.SET_NULL, null=True, related_name="materials") 
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, related_name="revision_materials")
    
    class Meta:
        db_table = "revision_materials"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}"

class AssessmentType(models.TextChoices):
    MCQ = "mcq", "Multiple Choice"
    FILE = "file", "File Upload"
    MIXED = "mixed", "Mixed"


class Assessment(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, related_name="assessments")
    teacher = models.ForeignKey('users.TeacherProfile', on_delete=models.CASCADE, related_name="assessments") 
    assessment_type = models.CharField(max_length=10, choices=AssessmentType.choices, default=AssessmentType.MCQ)
    due_date = models.DateTimeField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    

    class Meta:
        db_table = "assessments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "questions"
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order}: {self.text[:40]}"


class Choice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=1000)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "choices"

    def __str__(self):
        return f"{self.text[:30]} ({'✔' if self.is_correct else '✖'})"


class AssessmentAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="assignments")
    class_assigned = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True, related_name="assessments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "assessment_assignments"
        ordering = ["-assigned_at"]


class AssessmentSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey('users.StudentProfile', on_delete=models.CASCADE, related_name="assessment_submissions") 
    submitted_at = models.DateTimeField(default=timezone.now)
    file_url = models.URLField(max_length=500, null=True, blank=True)
    answers = models.JSONField(null=True, blank=True)
    grading = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("graded", "Graded"), ("late", "Late")],
        default="pending"
    )

    class Meta:
        db_table = "assessment_submissions"
        unique_together = ("assessment", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.assessment.title} - {self.student}"