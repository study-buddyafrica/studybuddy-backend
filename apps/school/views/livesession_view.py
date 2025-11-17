from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from rest_framework import generics, permissions

from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.school.models import LiveSession
from apps.school.serializers.livesession_serializer import LiveSessionSerializer
from apps.core.permissions import IsVerified,IsTeacherOrAdmin

class LiveSessionCreateView(generics.GenericAPIView):
    """
    Allows students to create a live session once a booking is allowed.
    Automatically generates a Google Meet link.
    """
    serializer_class = LiveSessionSerializer
    permission_classes = [IsAuthenticated,IsTeacherOrAdmin]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response(
            self.get_serializer(session).data,
            status=status.HTTP_201_CREATED,
        )
    

class LiveSessionUpdateView(generics.UpdateAPIView):
    """
    Allows teacher or admin to mark session as attended.
    Automatically triggers teacher payment and transaction logging.
    """
    queryset = LiveSession.objects.all()
    serializer_class = LiveSessionSerializer
    permission_classes = [IsAuthenticated,IsTeacherOrAdmin]

    def patch(self, request, *args, **kwargs):
        try:
            session = self.get_object()
        except LiveSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        if session.attended:
            return Response({"detail": "Session already marked as attended."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(
            session,
            data={"attended": True},
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_session = serializer.save()

        return Response(
            self.get_serializer(updated_session).data,
            status=status.HTTP_200_OK,
        )


class LiveSessionListView(generics.ListAPIView):
    """
    List live sessions:
      - Superuser: sees all sessions
      - Teachers: sees sessions they are teaching
      - Students: sees sessions they booked
    """
    serializer_class = LiveSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user

        qs = LiveSession.objects.select_related(
            "teacher__user",
            "session__student__user"
        )

        if user.is_superuser:
            return qs.order_by("-started_at")

        student_qs = qs.filter(session__student__user=user)

        teacher_qs = qs.filter(teacher__user=user)

        return (student_qs | teacher_qs).distinct().order_by("-started_at")
