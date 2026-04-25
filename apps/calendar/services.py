"""CalendarService — creates/updates CalendarEvent records from signals."""
from __future__ import annotations


class CalendarService:
    @staticmethod
    def on_session_booking_save(booking) -> None:
        """Create/update CalendarEvent rows for teacher, student, and parents."""
        from apps.calendar.models import CalendarEvent

        terminal_statuses = ("cancelled", "declined")
        new_status = "cancelled" if booking.status in terminal_statuses else "scheduled"

        title = f"Session with {booking.teacher.user.get_full_name() or booking.teacher.user.email}"

        # Teacher event
        CalendarEvent.objects.update_or_create(
            reference_id=booking.id,
            teacher=booking.teacher,
            student=None,
            parent=None,
            defaults={
                "title": title,
                "start_datetime": booking.scheduled_start,
                "end_datetime": booking.scheduled_end or booking.scheduled_start,
                "event_type": "session_booking",
                "status": new_status,
            },
        )

        # Student event
        CalendarEvent.objects.update_or_create(
            reference_id=booking.id,
            teacher=None,
            student=booking.student,
            parent=None,
            defaults={
                "title": title,
                "start_datetime": booking.scheduled_start,
                "end_datetime": booking.scheduled_end or booking.scheduled_start,
                "event_type": "session_booking",
                "status": new_status,
            },
        )

        # Parent events — one row per parent of the student
        for parent_child in booking.student.child_parents.select_related("parent"):
            CalendarEvent.objects.update_or_create(
                reference_id=booking.id,
                teacher=None,
                student=None,
                parent=parent_child.parent,
                defaults={
                    "title": title,
                    "start_datetime": booking.scheduled_start,
                    "end_datetime": booking.scheduled_end or booking.scheduled_start,
                    "event_type": "session_booking",
                    "status": new_status,
                },
            )

    @staticmethod
    def on_live_session_save(live_session) -> None:
        """Create/update CalendarEvent rows for teacher and all enrolled students."""
        from apps.calendar.models import CalendarEvent
        from apps.school.models import CourseEnrollment

        title = live_session.title or "Live Session"

        if live_session.teacher:
            CalendarEvent.objects.update_or_create(
                reference_id=live_session.id,
                teacher=live_session.teacher,
                student=None,
                parent=None,
                defaults={
                    "title": title,
                    "start_datetime": live_session.started_at,
                    "end_datetime": live_session.ended_at,
                    "event_type": "live_session",
                    "status": "scheduled",
                },
            )

        if live_session.course_id:
            enrollments = CourseEnrollment.objects.filter(
                course_id=live_session.course_id, is_active=True
            ).select_related("student")
            for enrollment in enrollments:
                CalendarEvent.objects.update_or_create(
                    reference_id=live_session.id,
                    teacher=None,
                    student=enrollment.student,
                    parent=None,
                    defaults={
                        "title": title,
                        "start_datetime": live_session.started_at,
                        "end_datetime": live_session.ended_at,
                        "event_type": "live_session",
                        "status": "scheduled",
                    },
                )
