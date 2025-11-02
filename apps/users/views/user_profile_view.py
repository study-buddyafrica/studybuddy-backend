from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from apps.users.serializers.create_user_profile_serializer import UserRegistrationSerializer
from apps.core.models import User

class UserRegistrationView(generics.CreateAPIView):
    """
    Handles user registration.
    Automatically creates related profiles based on user role.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

