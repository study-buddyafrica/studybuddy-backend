from django.urls import path
from apps.school.views.school_view import SchoolListCreateView
from apps.school.views.session_booking_view import (
    SessionBookingCreateView,
    SessionBookingCreateUpdateView,
    SessionBookingListView,
)
from apps.school.views.livesession_view import (
    LiveSessionCreateView,LiveSessionUpdateView,
    LiveSessionListView
)

urlpatterns = [
    path("schools/", SchoolListCreateView.as_view(), name="school-list-create"),
    path("live-sessions/", LiveSessionListView.as_view(), name="livesession-list-view"),
    path("booked-sessions/", SessionBookingListView.as_view(), name="bookedsession-list-view"),
    path("student/session-bookings/", SessionBookingCreateView.as_view(), name="session-booking-create"),
    path("student/session-booking/update/<uuid:pk>/", SessionBookingCreateUpdateView.as_view(), name="session-booking-update"),
    path("teacher/live-session/", LiveSessionCreateView.as_view(), name="live-session-create"),
    path("teacher/live-session/update/<uuid:pk>/", LiveSessionUpdateView.as_view(), name="live-session-update"),

]
