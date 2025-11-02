from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.users.views.user_profile_view import UserRegistrationView
from apps.users.views.list_users_view import UserListView,UserDetailView
from apps.users.views.delete_user import UserDeleteView
from apps.users.views.update_user import UserUpdateView
from apps.users.views.list_teachers_view import TeacherListView


user_router = DefaultRouter()

urlpatterns = [
    path("users/users-list/", UserListView.as_view(), name="user-list"),
    path("users/register/", UserRegistrationView.as_view(), name="user-register"),
    path("user/retrieve/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("user/update/<uuid:pk>/", UserUpdateView.as_view(), name="user-update"),
    path("user/delete/<uuid:pk>/", UserDeleteView.as_view(), name="user-delete"),
     path("teachers/list", TeacherListView.as_view(), name="teacher-list"),
   
]+ user_router.urls
