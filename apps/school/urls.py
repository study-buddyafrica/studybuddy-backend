from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.school.views.peer_to_peer_session_view import PeerLiveSessionViewSet
from apps.school.views.school_view import SchoolListCreateView
from apps.school.views.subject_view import SubjectViewSet
from apps.school.views.grade_view import GradeViewSet
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
    RevisionMaterialCreateListView,
    AssessmentRetrieveUpdateView
)
from apps.school.views.course_enrollment_view import (
    CourseEnrollmentView, ListEnrolledCourseView
)
from apps.school.views.course_sessions_views import (
    CourseLiveSessionCreateView,
    StudentCourseLiveSessionListView
)

school_router = DefaultRouter()
school_router.register(r'subjects', SubjectViewSet)
school_router.register(r'grades', GradeViewSet)
school_router.register(
    r"peer-to-peer-sessions",
    PeerLiveSessionViewSet, 
    basename="peer-live-session"
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
    path(
        "assessments/", 
        AssessmentCreateListView.as_view(), 
        name="assessments-list-create"
    ),
    path(
        "assessments/<uuid:id>/", 
        AssessmentRetrieveUpdateView.as_view(), 
        name="assessments-detail-update"
    ),
    path(
        "courses/", 
        CourseCreateListView.as_view(), 
        name="course-list-create"
    ),
    path(
        "courses/enrollments/", 
        CourseEnrollmentView.as_view(), 
        name="course-enrollments"
    ),
    path(
        "student/enrolled/courses/",
        ListEnrolledCourseView.as_view(),
        name='enrolled-courses'
    ),
    path(
        "teacher/course/live-lession/",
        CourseLiveSessionCreateView.as_view(),
        name="course-live-lession-create"
    ),

    path(
        "student/join/lessions/",
        StudentCourseLiveSessionListView.as_view(),
        name="join-lession"
    ),

]
urlpatterns +=school_router.urls
