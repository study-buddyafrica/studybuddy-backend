from rest_framework import generics, permissions, filters
from apps.school.models import School
from apps.school.serializers.school_serializer import SchoolSerializer

class SchoolListCreateView(generics.ListCreateAPIView):
    """
    - Anyone can view schools
    - Only Admins or Verified Teachers can create
    """
    serializer_class = SchoolSerializer
    queryset = School.objects.select_related("created_by").only(
        "id", "name", "address", "city", "country", "contact", "created_by__first_name"
    )
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "city", "country"]
    ordering_fields = ["name", "city", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_authenticated or not self.request.user.is_staff:
            qs = qs.filter(is_approved=True)
        return qs

    def perform_create(self, serializer):
        serializer.save()
