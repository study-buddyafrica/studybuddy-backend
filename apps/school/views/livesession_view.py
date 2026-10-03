from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions
from urllib.parse import urlparse

from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.school.models import LiveSession
from apps.school.serializers.livesession_serializer import LiveSessionSerializer
from apps.core.permissions import IsVerified, IsTeacherOrAdmin
from apps.core.utils.dailyco import DailyCoAPI


class LiveSessionCreateView(generics.GenericAPIView):
    """
    Allows students to create a live session once a booking is allowed.
    Automatically generates a Google Meet link.
    """

    serializer_class = LiveSessionSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
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
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def patch(self, request, *args, **kwargs):
        try:
            session = self.get_object()
        except LiveSession.DoesNotExist:
            return Response(
                {"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if related session booking is already marked attended
        if session.session and session.session.attended:
            return Response(
                {"detail": "Session already marked as attended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark the related SessionBooking as attended, not LiveSession
        if session.session:
            session.session.attended = True
            session.session.save(update_fields=["attended"])

        # Update LiveSession end time
        serializer = self.get_serializer(
            session, data={}, partial=True, context={"request": request}
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
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    pagination_class = StandardResultsSetPagination
    queryset = LiveSession.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LiveSession.objects.none()

        user = self.request.user

        if not getattr(user, "is_authenticated", False):
            return LiveSession.objects.none()

        qs = LiveSession.objects.select_related(
            "teacher__user", "session__student__user"
        )

        if user.is_superuser:
            return qs.order_by("-started_at")

        student_qs = qs.filter(session__student__user=user)

        teacher_qs = qs.filter(teacher__user=user)

        return (student_qs | teacher_qs).distinct().order_by("-started_at")


class DailyTokenView(generics.GenericAPIView):
    """Issue a fresh Daily token to an authorized live-session participant."""

    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get(self, request, pk):
        try:
            live_session = LiveSession.objects.select_related(
                "teacher__user", "session__student__user"
            ).get(pk=pk)
        except LiveSession.DoesNotExist:
            return Response(
                {"detail": "Live session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user
        is_teacher = live_session.teacher and live_session.teacher.user_id == user.id
        is_student = (
            live_session.session
            and live_session.session.student
            and live_session.session.student.user_id == user.id
        )

        if not (user.is_staff or is_teacher or is_student):
            return Response(
                {"detail": "You are not allowed to join this session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        source_url = (
            live_session.teacher_meeting_link
            if is_teacher or user.is_staff
            else live_session.student_meeting_link
        )
        room_name = urlparse(source_url or "").path.strip("/").split("/")[-1]
        if not room_name:
            return Response(
                {"detail": "This session does not have a Daily room."},
                status=status.HTTP_409_CONFLICT,
            )

        display_name = f"{user.first_name} {user.last_name}".strip() or user.username
        token = DailyCoAPI().create_token(
            room_name=room_name,
            user_id=str(user.id),
            user_name=display_name,
            is_owner=bool(user.is_staff or is_teacher),
        )
        return Response(
            {
                "room_url": token["room_url"].split("?", 1)[0],
                "token": token["token"],
                "user_name": display_name,
                "is_owner": token["is_owner"],
            },
            status=status.HTTP_200_OK,
        )
