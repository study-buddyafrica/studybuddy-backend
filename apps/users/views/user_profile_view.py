from rest_framework import generics, permissions
from rest_framework.throttling import AnonRateThrottle
from apps.users.serializers.create_user_profile_serializer import UserRegistrationSerializer


class RegistrationThrottle(AnonRateThrottle):
    """Rate limit registration endpoint to 5 attempts per minute."""
    scope = "login"


class UserRegistrationView(generics.CreateAPIView):
    """
    Handles user registration.
    Automatically creates related profiles based on user role.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]

