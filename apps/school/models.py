import uuid
from django.utils import timezone
from django.db import models
from djmoney.models.fields import MoneyField

from apps.core.models import Core
from apps.core.utils.countries import AfricanCountry

class School(Core):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    country = models.CharField(
        max_length=50,
        choices=AfricanCountry.choices,
        default=AfricanCountry.KENYA,
    )
    contact = models.CharField(max_length=50)
    is_approved = models.BooleanField(default=False)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
        )
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

class Subject(Core):
    """
    Represents a subject taught in a 
    specific class (e.g., Mathematics, Biology).
    """ 
    name = models.CharField(max_length=150, db_index=True) 
    description = models.TextField(blank=True, null=True) 
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    ) 
     
    
    def __str__(self): return f"{self.name}" 
    
    class Meta: 
        db_table = "subjects" 
        ordering = ["name"] 
        indexes = [ models.Index(fields=["name"]),]

class Grade(Core):
    """
    Represents academic or professional levels.
    Can be used for primary, secondary, college, university, or other skill-based courses.
    """

    class GradeLevel(models.TextChoices):
        GRADE_1 = "Grade 1", "Grade 1"
        GRADE_2 = "Grade 2", "Grade 2"
        GRADE_3 = "Grade 3", "Grade 3"
        GRADE_4 = "Grade 4", "Grade 4"
        GRADE_5 = "Grade 5", "Grade 5"
        GRADE_6 = "Grade 6", "Grade 6"
        GRADE_7 = "Grade 7", "Grade 7"
        GRADE_8 = "Grade 8", "Grade 8"
        GRADE_9 = "Grade 9", "Grade 9"
        GRADE_10 = "Grade 10", "Grade 10"
        GRADE_11 = "Grade 11", "Grade 11"
        GRADE_12 = "Grade 12", "Grade 12"
        COLLEGE = "College", "College"
        UNIVERSITY = "University", "University"
        PROFESSIONAL = "Professional", "Professional"
        GENERAL = "General", "General"  

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    level = models.CharField(
        max_length=50,
        choices=GradeLevel.choices,
        default=GradeLevel.GENERAL,
        db_index=True
    )
    

    class Meta:
        db_table = "grades"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.level}"


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"

class Course(Core):
    """
    A course created by a teacher (e.g., Mathematics - Grade 9, Life Skills)
    """
    is_active = models.BooleanField(default=True)
    is_universal = models.BooleanField(default=False)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    subject = models.ForeignKey(
        'school.Subject',
        on_delete=models.CASCADE,
        related_name="subject_course"
    )
    grade = models.ForeignKey(
        Grade, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="courses"
    )
    title = models.CharField(
        max_length=150, 
        db_index=True
    )
    description = models.TextField(
        blank=True, 
        null=True
    )
    price = MoneyField(
        max_digits=10, 
        decimal_places=2, 
        default_currency="KES", 
        default=0
    )
    cover_image = models.ImageField(
        upload_to="course-contents/",
        blank=True, 
        null=True
    )
    country = models.CharField(
        max_length=50,
        choices=AfricanCountry.choices,
        null=True,blank=True
    )
    teacher = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.CASCADE,
        related_name="teacher_courses",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if self.is_universal:
            self.country = None
        else:
            if not self.country:
                raise ValueError(
                    "Country is required for " \
                    "non-universal courses."
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} \
            ({self.grade or \
            'General'}) by teacher \
            {self.teacher.user.username}"

    class Meta:
        db_table = "courses"
        ordering = ["title"]


class CourseEnrollment(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        "Course", on_delete=models.CASCADE, related_name="enrollments"
    )
    student = models.ForeignKey(
        "users.StudentProfile", on_delete=models.CASCADE, related_name="enrollments"
    )
    purchased_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    transaction = models.ForeignKey(
        "transactions.Transaction", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "course_enrollments"
        unique_together = ("course", "student")
    
    @property
    def is_valid(self):
        return self.is_active and (not self.expires_at or self.expires_at > timezone.now())

    def __str__(self):
        return f"{self.student.user.first_name} - {self.course.title}"


class Topic(Core):
    """High-level topic under a specific course."""
    title = models.CharField(max_length=200)
    is_locked = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    content_file = models.FileField(
        upload_to="topics/%Y/%m/%d/",
        blank=True,
        null=True,
        help_text="Upload PDF, video, or other resources."
    )
    description = models.TextField(
        blank=True, null=True
    )


    class Meta:
        db_table = "topics"
        ordering = ["course", "order"]
        indexes = [
            models.Index(fields=["course"]),
        ]

    def __str__(self):
        return f"{self.course.title}: {self.title}"


class Subtopic(Core):
    """Subtopic or lesson content under a topic."""
    title = models.CharField(max_length=200)
    is_locked = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    content = models.TextField(blank=True, null=True)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="subtopics",
    )
    content_file = models.FileField(
        upload_to="subtopics/%Y/%m/%d/",
        blank=True,
        null=True,
        help_text="Upload PDF, video, or other resources."
    )
    

    class Meta:
        db_table = "subtopics"
        ordering = ["topic", "order"]
        indexes = [
            models.Index(fields=["topic"]),
        ]

    def __str__(self):
        return f"{self.topic.title} → {self.title}"
    
    @property
    def has_content(self):
        """Check if the subtopic has either text or file content."""
        return bool(self.content) or bool(self.content_file)


class SessionBooking(Core):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        'users.StudentProfile', 
        on_delete=models.CASCADE, 
        related_name="student_session_bookings" 
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(null=True, blank=True)
    is_allowed = models.BooleanField(default=False)
    attended = models.BooleanField(default=False)
    teacher = models.ForeignKey(
        'users.TeacherProfile', 
        on_delete=models.CASCADE, 
        related_name="teacher_session_bookings" 
    )
    course = models.ForeignKey(
    Course, 
    on_delete=models.SET_NULL, 
    null=True, 
    blank=True, 
    related_name="session_bookings"   
    )


    class Meta:
        db_table = "session_bookings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Booking: {self.student} ({self.status})"

class LiveSession(Core):
    capacity = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    student_meeting_link = models.URLField(max_length=1000, null=True, blank=True)
    teacher_meeting_link = models.URLField(max_length=1000, null=True, blank=True)
    whiteboard_link = models.URLField(max_length=500, null=True,blank=True)
    session = models.OneToOneField(
        SessionBooking,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="live_session",
    )
    course = models.ForeignKey( 
        Course,
        null=True,
        blank=True,
        related_name="live_lessons",
        on_delete=models.CASCADE,
    )
    teacher = models.ForeignKey(
        'users.TeacherProfile', 
        on_delete=models.CASCADE, 
        related_name="live_sessions"  
    )

    def __str__(self):
        return f"{self.title} ({self.started_at:%Y-%m-%d})"


class RevisionMaterial(Core):
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    file= models.FileField(blank=True, null=True)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    uploaded_by = models.ForeignKey(
        'users.TeacherProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="materials"
    ) 
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, 
        null=True, 
        related_name="revision_materials"
    )
    
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
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(null=True, blank=True)
    duration =models.TimeField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="assessments"
    )
    teacher = models.ForeignKey(
        'users.TeacherProfile', 
        on_delete=models.CASCADE, 
        related_name="assessments"
    ) 
    assessment_type = models.CharField(
        max_length=10, 
        choices=AssessmentType.choices, 
        default=AssessmentType.MCQ
    )
    
    class Meta:
        db_table = "assessments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}"


class Question(models.Model):
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    assessment = models.ForeignKey(
        Assessment, 
        on_delete=models.CASCADE, 
        related_name="questions"
    )
    

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
    
    @property
    def is_late(self):
        return (
            self.assessment.due_date
            and self.submitted_at > self.assessment.due_date
        )


class SubtopicProgress(models.Model):
    student = models.ForeignKey('users.StudentProfile', on_delete=models.CASCADE)
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "subtopic")


class TopicProgress(models.Model):
    student = models.ForeignKey('users.StudentProfile', on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "topic")


class CourseProgress(models.Model):
    student = models.ForeignKey('users.StudentProfile', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "course")
