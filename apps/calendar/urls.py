from django.urls import path
from apps.calendar.views import CalendarEventListView

urlpatterns = [
    path("calendar/events/", CalendarEventListView.as_view(), name="calendar-events"),
]
