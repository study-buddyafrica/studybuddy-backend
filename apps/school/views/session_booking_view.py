from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.core.exceptions import ValidationError
import uuid

from apps.school.models import SessionBooking
from apps.school.serializers.session_booking_serializer import SessionBookingSerializer
from apps.transactions.models import Transaction

class SessionBookingCreateView(generics.CreateAPIView):
    serializer_class = SessionBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SessionBooking.objects.filter(student__user=self.request.user)


class IsStudent(permissions.BasePermission):
    """Custom permission — only allow logged-in students."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "student_profile")
        )

class SessionBookingCreateUpdateView(generics.GenericAPIView):
    """
    Handles:
    - Student creates or reschedules session (with wallet deduction and transaction logging)
    - Auto-credit teacher when `attended=True`
    """
    serializer_class = SessionBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SessionBooking.objects.select_related("student__user", "teacher__user")

    def _log_transaction(self, wallet, amount, tx_type, description, related_tx=None):
        """Helper: Create a transaction record."""
        return Transaction.objects.create(
            wallet=wallet,
            transaction_identifier=str(uuid.uuid4()),
            amount=amount,
            transaction_type=tx_type,
            payment_method="wallet",
            status="success",
            description=description,
            related_transaction=related_tx,
            metadata_info={
                "timestamp": str(timezone.now()),
                "initiated_by": wallet.user.email if hasattr(wallet.user, "email") else str(wallet.id),
            },
        )

    def post(self, request, *args, **kwargs):
        """Create new session booking with wallet deduction and transaction log."""
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        wallet = booking.student.user.wallet
        amount = booking.cost

        self._log_transaction(
            wallet,
            amount,
            "payment",
            f"Payment for session booking with teacher {booking.teacher.user.get_full_name()}",
        )
        return Response(self.get_serializer(booking).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk=None, *args, **kwargs):
        """
        Handles:
        - Rescheduling by student (refund + re-deduct)
        - Marking as attended (teacher payout)
        """
        try:
            booking = self.get_queryset().get(pk=pk)
        except SessionBooking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        attended_flag = request.data.get("attended", None)

        if attended_flag is True and not booking.attended:
            if user.is_staff or hasattr(user, "teacher_profile"):
                with transaction.atomic():
                    booking.attended = True
                    booking.status = "completed"
                    booking.save()

                    # Credit teacher wallet
                    teacher_wallet = booking.teacher.user.wallet
                    teacher_wallet.balance.amount += booking.cost
                    teacher_wallet.save()

                    # Log teacher credit transaction
                    teacher_tx = self._log_transaction(
                        teacher_wallet,
                        booking.cost,
                        "deposit",
                        f"Earnings for attended session with student {booking.student.user.get_full_name()}",
                    )

                    self._log_transaction(
                        booking.student.user.wallet,
                        booking.cost,
                        "transfer",
                        f"Transfer to {booking.teacher.user.get_full_name()} for completed session",
                        related_tx=teacher_tx,
                    )

                return Response(
                    {"detail": "Session marked as attended and teacher credited."},
                    status=status.HTTP_200_OK,
                )
            return Response({"detail": "Only teacher or admin can mark attendance."}, status=status.HTTP_403_FORBIDDEN)

        if hasattr(user, "student_profile"):
            if booking.scheduled_start <= timezone.now():
                return Response(
                    {"detail": "Cannot modify a session that has already started."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if booking.scheduled_start - timezone.now() <= timedelta(hours=1):
                return Response(
                    {"detail": "Rescheduling allowed only at least 1 hour before start."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_start = request.data.get("scheduled_start")
            if not new_start:
                return Response({"detail": "New start time required."}, status=status.HTTP_400_BAD_REQUEST)

            teacher = booking.teacher
            student_wallet = booking.student.user.wallet
            teacher_rate = teacher.hourly_rate.amount

            with transaction.atomic():
            
                student_wallet.balance.amount += booking.cost
                student_wallet.save()

                refund_tx = self._log_transaction(
                    student_wallet,
                    booking.cost,
                    "refund",
                    f"Refund for rescheduling session with {teacher.user.get_full_name()}",
                )

                from datetime import datetime
                new_start_dt = datetime.fromisoformat(new_start)
                affordable_hours = int(student_wallet.balance.amount // teacher_rate)
                if affordable_hours < 1:
                    transaction.set_rollback(True)
                    return Response(
                        {"detail": "Insufficient wallet balance to reschedule."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                new_end = new_start_dt + timedelta(hours=affordable_hours)
                total_cost = teacher_rate * affordable_hours

    
                student_wallet.balance.amount -= total_cost
                student_wallet.save()

                payment_tx = self._log_transaction(
                    student_wallet,
                    total_cost,
                    "payment",
                    f"Payment for rescheduled session with {teacher.user.get_full_name()}",
                    related_tx=refund_tx,
                )

                booking.scheduled_start = new_start
                booking.scheduled_end = new_end
                booking.cost = total_cost
                booking.save()

            return Response(self.get_serializer(booking).data, status=status.HTTP_200_OK)

        return Response({"detail": "Action not permitted."}, status=status.HTTP_403_FORBIDDEN)