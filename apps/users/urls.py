from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.users.views.teachers_verification_views import TeacherProfileViewSet
from apps.users.views.user_profile_view import UserRegistrationView
from apps.users.views.list_users_view import UserListView, UserDetailView
from apps.users.views.delete_user import UserDeleteView
from apps.users.views.update_user import UserUpdateView
from apps.users.views.list_teachers_view import TeacherListView
from apps.users.views.student_lead_view import StudentLeadViewSet
from apps.users.views.update_profile_views import (
    ParentProfileUpdateView,
    StudentProfileUpdateView,
    TeacherProfileUpdateView,
)
from apps.users.views.profile_views import (
    TeacherProfileView,
    StudentProfileView,
    ParentProfileView,
    ParentChildrenView,
    ParentRegisterStudentView,
)

user_router = DefaultRouter()
user_router.register("teachers", TeacherProfileViewSet, basename="teacher")
user_router.register(r"student-leads", StudentLeadViewSet, basename="student-lead")

urlpatterns = [
    path("users/register/", UserRegistrationView.as_view(), name="user-register"),
    path("users/users-list/", UserListView.as_view(), name="user-list"),
    path("user/retrieve/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("user/update/<uuid:pk>/", UserUpdateView.as_view(), name="user-update"),
    path("user/delete/<uuid:pk>/", UserDeleteView.as_view(), name="user-delete"),
    path("teachers/list", TeacherListView.as_view(), name="teacher-list"),
    path(
        "parent/profile/update/<uuid:id>/",
        ParentProfileUpdateView.as_view(),
        name="parent-profile-update",
    ),
    # Legacy frontend compatibility for undefined id update route
    path(
        "parent/profile/update/undefined/",
        ParentProfileView.as_view(),
        name="parent-profile-update-undefined",
    ),
    path(
        "parent/profile/update/",
        ParentProfileView.as_view(),
        name="parent-profile-update-current",
    ),
    path(
        "student/profile/update/<uuid:id>/",
        StudentProfileUpdateView.as_view(),
        name="student-profile-update",
    ),
    # Legacy frontend compatibility for numeric/placeholder ids
    path(
        "student/profile/update/<int:id>/",
        StudentProfileView.as_view(),
        name="student-profile-update-int",
    ),
    path(
        "student/profile/update/undefined/",
        StudentProfileView.as_view(),
        name="student-profile-update-undefined",
    ),
    path(
        "student/profile/update/",
        StudentProfileView.as_view(),
        name="student-profile-update-current",
    ),
    path(
        "teacher/profile/update/",
        TeacherProfileUpdateView.as_view(),
        name="teacher-profile-update",
    ),
    # New RESTful Profile Endpoints
    path("teacher/profile/", TeacherProfileView.as_view(), name="teacher-profile"),
    path("student/profile/", StudentProfileView.as_view(), name="student-profile"),
    path("parent/profile/", ParentProfileView.as_view(), name="parent-profile"),
    path("parent/children/", ParentChildrenView.as_view(), name="parent-children"),
    path(
        "parent/register-student/",
        ParentRegisterStudentView.as_view(),
        name="parent-register-student",
    ),
    path(
        "parent/register-student",
        ParentRegisterStudentView.as_view(),
        name="parent-register-student-no-slash",
    ),
] + user_router.urls
