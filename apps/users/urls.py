from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.users.views.teachers_verification_views import TeacherProfileViewSet
from apps.users.views.user_profile_view import UserRegistrationView
from apps.users.views.list_users_view import UserListView,UserDetailView
from apps.users.views.delete_user import UserDeleteView
from apps.users.views.update_user import UserUpdateView
from apps.users.views.list_teachers_view import TeacherListView
from apps.users.views.student_lead_view import StudentLeadViewSet
from apps.users.views.update_profile_views import (
    ParentProfileUpdateView,StudentProfileUpdateView,
    TeacherProfileUpdateView
)

user_router = DefaultRouter()
user_router.register(
    "teachers", 
    TeacherProfileViewSet, 
    basename="teacher"
)
user_router.register(
    r"student-leads",
    StudentLeadViewSet,
    basename="student-lead"
)

urlpatterns = [
    path(
        "users/register/", 
        UserRegistrationView.as_view(), 
        name="user-register"
    ),
    path(
        "users/users-list/", 
        UserListView.as_view(), 
        name="user-list"
    ),
    path(
        "user/retrieve/<uuid:pk>/", 
        UserDetailView.as_view(), 
        name="user-detail"
    ),
    path(
        "user/update/<uuid:pk>/", 
        UserUpdateView.as_view(), 
        name="user-update"
    ),
    path(
        "user/delete/<uuid:pk>/", 
        UserDeleteView.as_view(), 
        name="user-delete"
    ),
    path(
        "teachers/list", 
        TeacherListView.as_view(), 
        name="teacher-list"
    ),
    path(
        "parent/profile/update/<uuid:id>/", 
        ParentProfileUpdateView.as_view(), 
        name="parent-profile-update"
    ),
    path(
        "student/profile/update/<uuid:id>/", 
        StudentProfileUpdateView.as_view(), 
        name="student-profile-update"
    ),
    path(
        "teacher/profile/update/", 
        TeacherProfileUpdateView.as_view(), 
        name="teacher-profile-update"
    ),
   
]+ user_router.urls
