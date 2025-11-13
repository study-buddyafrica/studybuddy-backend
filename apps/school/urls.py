from django.urls import path

from apps.school.views.school_view import SchoolListCreateView
from apps.school.views.join_session_view import StudentJoinLiveSessionView
from apps.school.views.course_registration_view import (
    CourseCreateListView,TopicCreateListView,
    SubtopicCreateListView
)
from apps.school.views.session_booking_view import (
    SessionBookingCreateUpdateView,
    SessionBookingListView,
)
from apps.school.views.livesession_view import (
    LiveSessionCreateView,LiveSessionUpdateView,
    LiveSessionListView
)
from apps.school.views.assessments_views import (
    AssessmentCreateListView,
    RevisionMaterialCreateListView
)

urlpatterns = [
    path(
        "schools/", 
        SchoolListCreateView.as_view(), 
        name="school-list-create"
        ),
    path(
        "student/live-session/<uuid:session_booking_id>/join/", 
        StudentJoinLiveSessionView.as_view(), 
        name='join-livesession'
        ),
    path(
        "live-sessions/", 
        LiveSessionListView.as_view(), 
        name="livesession-list-view"
        ),
    path(
        "booked-sessions/", 
        SessionBookingListView.as_view(), 
        name="bookedsession-list-view"
        ),
    path(
        "student/session-bookings/",
        SessionBookingCreateUpdateView.as_view(),
        name="session-booking-create"
    ),
    path(
        "student/session-bookings/<uuid:pk>/",
        SessionBookingCreateUpdateView.as_view(),
        name="session-booking-update"
    ),
    path(
        "teacher/live-session/", 
        LiveSessionCreateView.as_view(), 
        name="live-session-create"
        ),
    path(
        "teacher/live-session/update/<uuid:pk>/", 
        LiveSessionUpdateView.as_view(), 
        name="live-session-update"
        ),
    path(
        "courses/", 
        CourseCreateListView.as_view(), 
        name="course-list-create"
        ),
    path(
        "topics/", 
        TopicCreateListView.as_view(), 
        name="topic-list-create"
        ),
    path(
        "subtopics/", 
        SubtopicCreateListView.as_view(), 
        name="subtopic-list-create"
        ),
    path(
        "revision-materials/", 
        RevisionMaterialCreateListView.as_view(), 
        name="revision-materials"
        ),
    path(
        "assessments/", 
        AssessmentCreateListView.as_view(), 
        name="assessments"
        ),
]
