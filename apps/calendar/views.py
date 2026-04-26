from rest_framework import generics, permissions
from apps.calendar.models import CalendarEvent
from apps.calendar.serializers import CalendarEventSerializer


class CalendarEventListView(generics.ListAPIView):
    """
    GET /api/calendar/events/
    Returns CalendarEvent records for the authenticated user, filtered by role.
    Supports optional start_date / end_date query params.
    """
    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CalendarEvent.objects.all()

        if hasattr(user, "teacher_profile"):
            qs = qs.filter(teacher=user.teacher_profile)
        elif hasattr(user, "student_profile"):
            qs = qs.filter(student=user.student_profile)
        elif hasattr(user, "parent_profile"):
            qs = qs.filter(parent=user.parent_profile)
        else:
            return CalendarEvent.objects.none()

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(start_datetime__gte=start_date)
        if end_date:
            qs = qs.filter(start_datetime__lte=end_date)

        return qs.order_by("start_datetime")
