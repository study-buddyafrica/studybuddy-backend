from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.users.views.user_profile_view import UserRegistrationView
from apps.users.views.list_users_view import UserListView

user_router = DefaultRouter()


urlpatterns = [
    path("users/users-list/", UserListView.as_view(), name="user-list"),
    path("users/register/", UserRegistrationView.as_view(), name="user-register"),
   
]+ user_router.urls
