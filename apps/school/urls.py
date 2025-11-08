from django.urls import path
from apps.school.views.school_view import SchoolListCreateView
from apps.school.views.session_booking_view import SessionBookingCreateView,SessionBookingCreateUpdateView
from apps.school.views.livesession_view import LiveSessionCreateView,LiveSessionUpdateView

urlpatterns = [
    path("schools/", SchoolListCreateView.as_view(), name="school-list-create"),
    path("student/session-bookings/", SessionBookingCreateView.as_view(), name="session-booking-create"),
    path("student/session-booking/update/<uuid:pk>/", SessionBookingCreateUpdateView.as_view(), name="session-booking-update"),
    path("teacher/live-session/", LiveSessionCreateView.as_view(), name="live-session-create"),
    path("teacher/live-session/update/<uuid:pk>/", LiveSessionUpdateView.as_view(), name="live-session-update"),

]

{
  "teacher_id": "23dcef70-dd8a-4e84-b915-52ec0f9c9379",
  "scheduled_start": "2025-11-08T11:19:05.738Z"
}