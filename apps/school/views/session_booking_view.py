from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from datetime import timedelta,datetime
from decimal import Decimal
import uuid

from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.school.models import SessionBooking
from apps.school.serializers.session_booking_serializer import SessionBookingSerializer
from apps.transactions.models import Transaction,Wallet


class SessionBookingCreateUpdateView(generics.GenericAPIView):
    """
    Handles:
    - Creating a booking (with immediate wallet deduction to system)
    - Rescheduling (refund + re-deduct)
    - Marking attendance (teacher payout)
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
        """Create new booking: deduct student's wallet → system wallet."""
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        user = request.user
        if not user.is_superuser:
            student_wallet = booking.student.user.wallet
            amount = booking.cost

            # Get or create system wallet
            system_wallet, _ = Wallet.objects.get_or_create(
                account_type="system",
                defaults={"balance": 0},
                user=user  # optional, can point to a system admin user
            )

            with transaction.atomic():
                if student_wallet.balance < amount:
                    return Response(
                        {"detail": "Insufficient balance."},
                        status=status.HTTP_402_PAYMENT_REQUIRED,
                    )

                student_wallet.balance -= amount
                student_wallet.save()

                system_wallet.balance += amount
                system_wallet.save()

                self._log_transaction(
                    student_wallet,
                    -amount.amount,
                    "debit",
                    f"Booking payment for {booking.teacher.user.get_full_name()}",
                )

                self._log_transaction(
                    system_wallet,
                    amount.amount,
                    "credit",
                    f"System hold for booking {booking.id}",
                )

        return Response(self.get_serializer(booking).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk=None, *args, **kwargs):
        """
        PATCH:
        - Mark attended (credit teacher)
        - Reschedule if >30min before start
        """
        try:
            booking = self.get_queryset().get(pk=pk)
        except SessionBooking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        attended_flag = request.data.get("attended", None)

        # --- Mark attendance ---
        if attended_flag is True and not booking.attended:
            if user.is_staff or hasattr(user, "teacher_profile"):
                with transaction.atomic():
                    booking.attended = True
                    booking.status = "completed"
                    booking.save()

                    teacher_wallet = booking.teacher.user.wallet
                    system_wallet = Wallet.objects.filter(account_type="system").first()
                    amount = booking.cost

                    if system_wallet and system_wallet.balance >= amount:
                        system_wallet.balance -= amount
                        teacher_wallet.balance += amount

                        system_wallet.save()
                        teacher_wallet.save()

                        teacher_tx = self._log_transaction(
                            teacher_wallet,
                            amount.amount,
                            "credit",
                            f"Payment for attended session with {booking.student.user.get_full_name()}",
                        )

                        self._log_transaction(
                            system_wallet,
                            -amount.amount,
                            "debit",
                            f"System payout to {booking.teacher.user.get_full_name()}",
                            related_tx=teacher_tx,
                        )

                    return Response(
                        {"detail": "Session marked as attended and teacher credited."},
                        status=status.HTTP_200_OK,
                    )
            return Response({"detail": "Only teacher or admin can mark attendance."}, status=status.HTTP_403_FORBIDDEN)

        # --- Reschedule ---
        if hasattr(user, "student_profile"):
            if booking.scheduled_start <= timezone.now():
                return Response(
                    {"detail": "Cannot modify a session that has already started."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if booking.scheduled_start - timezone.now() <= timedelta(minutes=30):
                return Response(
                    {"detail": "Rescheduling allowed only 30 minutes before start."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_start = request.data.get("scheduled_start")
            if not new_start:
                return Response({"detail": "New start time required."}, status=status.HTTP_400_BAD_REQUEST)

            teacher = booking.teacher
            student_wallet = booking.student.user.wallet
            system_wallet = Wallet.objects.filter(account_type="system").first()
            teacher_rate = float(teacher.hourly_rate.amount)

            with transaction.atomic():
                # refund from system → student
                system_wallet.balance -= booking.cost
                student_wallet.balance += booking.cost
                system_wallet.save()
                student_wallet.save()

                refund_tx = self._log_transaction(
                    student_wallet,
                    booking.cost.amount,
                    "refund",
                    f"Refund for rescheduled session with {teacher.user.get_full_name()}",
                )

                # compute new cost
                new_start_dt = datetime.fromisoformat(new_start)
                new_end = new_start_dt + timedelta(hours=float(booking.duration_hours))
                total_cost = Decimal(booking.duration_hours * teacher_rate)

                if student_wallet.balance < total_cost:
                    transaction.set_rollback(True)
                    return Response(
                        {"detail": "Insufficient wallet balance to reschedule."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                student_wallet.balance -= total_cost
                system_wallet.balance += total_cost
                student_wallet.save()
                system_wallet.save()

                payment_tx = self._log_transaction(
                    student_wallet,
                    -total_cost,
                    "payment",
                    f"Payment for rescheduled session with {teacher.user.get_full_name()}",
                    related_tx=refund_tx,
                )

                self._log_transaction(
                    system_wallet,
                    total_cost,
                    "hold",
                    f"System hold for rescheduled session {booking.id}",
                    related_tx=payment_tx,
                )

                booking.scheduled_start = new_start_dt
                booking.scheduled_end = new_end
                booking.cost = total_cost
                booking.save()

            return Response(self.get_serializer(booking).data, status=status.HTTP_200_OK)

        return Response({"detail": "Action not permitted."}, status=status.HTTP_403_FORBIDDEN)

class SessionBookingListView(generics.ListAPIView):
    """
    List live sessions:
      - Superuser: sees all sessions
      - Teachers: sees sessions they are teaching
      - Students: sees sessions they booked
    """
    serializer_class = SessionBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user

        qs = SessionBooking.objects.select_related(
            "teacher__user",
            "student__user"
        )

        if user.is_superuser:
            return qs.order_by("-scheduled_start")

        student_qs = qs.filter(student__user=user)

        teacher_qs = qs.filter(teacher__user=user)

        return (student_qs | teacher_qs).distinct().order_by("-scheduled_start")
