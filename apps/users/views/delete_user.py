from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.core.models import User


class UserDeleteView(generics.DestroyAPIView):
    """Delete user — superuser can delete any, user can only delete self"""
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_object(self):
        user = self.request.user
        target = get_object_or_404(User, pk=self.kwargs["pk"])
        if not user.is_superuser and user.id != target.id:
            self.permission_denied(self.request, message="You can only delete your own account.")
        return target

    def perform_destroy(self, instance):
        instance.delete()
        return Response({"message": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)