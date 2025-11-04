from django.urls import path
from apps.school.views.school_view import SchoolListCreateView
from apps.school.views.session_booking_view import SessionBookingCreateView,SessionBookingCreateUpdateView

urlpatterns = [
    path("schools/", SchoolListCreateView.as_view(), name="school-list-create"),
    path("student/session-bookings/", SessionBookingCreateView.as_view(), name="session-booking-create"),
    path("student/session-booking/update/<uuid:pk>/", SessionBookingCreateUpdateView.as_view(), name="session-booking-update"),

]
