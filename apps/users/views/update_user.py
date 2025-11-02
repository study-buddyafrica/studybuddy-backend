from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404
from apps.users.serializers.update_users_serializer import UserUpdateSerializer
from apps.core.models import User


class UserUpdateView(generics.UpdateAPIView):
    """Update user details — superuser can update any, user can only update self"""
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_object(self):
        user = self.request.user
        target = get_object_or_404(User, pk=self.kwargs["pk"])
        if not user.is_superuser and user.id != target.id:
            self.permission_denied(self.request, message="You can only update your own profile.")
        return target
