import uuid
from django.db import models
from apps.core.models import Core


class CalendarEvent(Core):
    EVENT_TYPE_CHOICES = [
        ("session_booking", "Session Booking"),
        ("live_session", "Live Session"),
        ("peer_session", "Peer Session"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField()

    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled", db_index=True
    )

    reference_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the source record (SessionBooking, LiveSession, or PeerSession)",
    )

    teacher = models.ForeignKey(
        "users.TeacherProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="calendar_events",
    )
    student = models.ForeignKey(
        "users.StudentProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="calendar_events",
    )
    parent = models.ForeignKey(
        "users.ParentProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="calendar_events",
    )

    class Meta:
        db_table = "calendar_events"
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["start_datetime", "status"]),
            models.Index(fields=["reference_id"]),
            models.Index(fields=["teacher"]),
            models.Index(fields=["student"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_datetime:%Y-%m-%d %H:%M})"
