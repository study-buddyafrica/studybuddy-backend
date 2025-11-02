from rest_framework import generics, permissions
from apps.users.models import TeacherProfile
from apps.users.serializers.list_teachers_serializer import TeacherProfileListSerializer


class TeacherListView(generics.ListAPIView):
    """
    Public endpoint for listing teachers.
    - Accessible to anyone (AllowAny)
    - Returns only verified teachers by default
    - Supports filtering by subject, hourly rate range, and verification status
    """
    serializer_class = TeacherProfileListSerializer
    permission_classes = [permissions.AllowAny]  
    def get_queryset(self):
        queryset = (
            TeacherProfile.objects.select_related("user")
            .prefetch_related("subjects")
            .only(
                "id",
                "bio",
                "hourly_rate",
                "is_verified",
                "user__first_name",
                "user__last_name",
            )
        )

        subject = self.request.query_params.get("subject")
        min_rate = self.request.query_params.get("min_rate")
        max_rate = self.request.query_params.get("max_rate")
        verified = self.request.query_params.get("verified")

        if subject:
            queryset = queryset.filter(subjects__name__icontains=subject.strip())

        if min_rate:
            queryset = queryset.filter(hourly_rate__gte=min_rate)

        if max_rate:
            queryset = queryset.filter(hourly_rate__lte=max_rate)

        if verified in ["true", "1", None]:
            queryset = queryset.filter(is_verified=True)
        elif verified in ["false", "0"]:
            queryset = queryset.filter(is_verified=False)

        return queryset.order_by("user__first_name")
