from rest_framework import viewsets
from apps.users.serializers.user_profile_serializer import UserRegistrationSerializer
from apps.core.models import User


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer

