from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.users.views.user_profile_view import UserViewSet

user_router = DefaultRouter()
user_router.register('users', UserViewSet)

urlpatterns = [
   
]+ user_router.urls
