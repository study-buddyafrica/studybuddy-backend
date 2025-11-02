from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.users.views.user_profile_view import UserViewSet
from apps.users.views.list_users_view import UserListView

user_router = DefaultRouter()
user_router.register('users', UserViewSet)

urlpatterns = [
    path("users-list", UserListView.as_view(), name="user-list"),
   
]+ user_router.urls
