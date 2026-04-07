from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from apps.users.serializers.list_users_serliazer import UserSerializer
from apps.core.models import User
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie


class UserListView(generics.ListAPIView):
    """
    Retrieve users with permission control:
      - Superuser → can view all users.
      - Regular user → can only view their own info.
    Supports filtering by role and email.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["email", "first_name", "last_name"]

    def get_queryset(self):
        user = self.request.user

        queryset = (
            User.objects.select_related(
                "teacher_profile", "parent_profile", "student_profile"
            )
            .only(
                "id",
                "email",
                "first_name",
                "last_name",
                "username",
                "role",
                "is_active",
                "is_staff",
                "account_confirmed",
                # profile PKs
                "teacher_profile__id",
                "parent_profile__id",
                "student_profile__id",
            )
            .order_by("-created_at")
        )

        role = self.request.query_params.get("role")
        email = self.request.query_params.get("email")

        if role:
            queryset = queryset.filter(role__iexact=role.strip())

        if email:
            queryset = queryset.filter(email__icontains=email.strip())

        if user.is_superuser:
            return queryset

        return queryset.filter(id=user.id)

    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        """Custom response structure."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"count": queryset.count(), "results": serializer.data})


class UserDetailView(generics.RetrieveAPIView):
    """Retrieve single user detail"""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=user.id)
