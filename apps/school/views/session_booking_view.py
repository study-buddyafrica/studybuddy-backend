from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from datetime import timedelta,datetime
from decimal import Decimal
from moneyed import Money
import uuid

from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.core.permissions import IsVerified
from apps.school.models import SessionBooking
from apps.users.models import TeacherProfile
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
    permission_classes = [permissions.IsAuthenticated,IsVerified]
    pagination_class = StandardResultsSetPagination

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
                "initiated_by": wallet.user.email if wallet.user else "system",
            },
        )

    def get(self, request, pk=None, *args, **kwargs):
        """
        GET compatibility handler:
        - /student/session-bookings/           -> list bookings for current user
        - /student/session-bookings/<uuid>/    -> retrieve one booking if owned/allowed
        - /student/session-bookings/undefined/ -> list bookings (legacy frontend fallback)
        """
        user = request.user
        qs = self.get_queryset()

        # Legacy frontend compatibility: treat undefined id as list request.
        if pk in (None, "", "undefined", "null"):
            if user.is_superuser:
                filtered = qs.order_by("-scheduled_start")
            else:
                student_qs = qs.filter(student__user=user)
                teacher_qs = qs.filter(teacher__user=user)
                filtered = (student_qs | teacher_qs).distinct().order_by("-scheduled_start")

            page = self.paginate_queryset(filtered)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(filtered, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        try:
            booking = qs.get(pk=pk)
        except SessionBooking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        if not user.is_superuser:
            is_owner = booking.student and booking.student.user_id == user.id
            is_teacher = booking.teacher and booking.teacher.user_id == user.id
            if not (is_owner or is_teacher):
                return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        Create a new booking:
        - Deduct student's wallet → system wallet
        """
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user

        system_wallet = Wallet.objects.filter(account_type="system").first()
        if not system_wallet:
            return Response(
                {"detail": "System wallet not found. Contact admin."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not user.is_superuser:
            try:
                student_wallet = user.wallet
            except Wallet.DoesNotExist:
                return Response(
                    {"detail": "Student wallet not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            teacher_id = serializer.validated_data.get("teacher_id")
            duration_hours = serializer.validated_data.get("duration_hours")
            scheduled_start = serializer.validated_data.get("scheduled_start")
            course = serializer.validated_data.get("course")

            teacher = TeacherProfile.objects.get(id=teacher_id)
            teacher_rate = float(teacher.hourly_rate)
            total_cost = Decimal(duration_hours * teacher_rate)
            amount = Money(total_cost, "KES")

            if student_wallet.balance < amount:
                return Response(
                    {"detail": "Insufficient balance."},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

            scheduled_end = scheduled_start + timedelta(hours=duration_hours)

            with transaction.atomic():
                student_wallet.balance -= amount
                student_wallet.save()
                system_wallet.balance += amount
                system_wallet.save()

                Transaction.objects.create(
                    wallet=student_wallet,
                    transaction_identifier=str(uuid.uuid4()),
                    amount=-amount.amount,
                    transaction_type="debit",
                    payment_method="wallet",
                    status="success",
                    description=f"Booking payment for teacher {teacher.user.username}",
                    metadata_info={"session_booking": str(teacher.id)},
                )

                Transaction.objects.create(
                    wallet=system_wallet,
                    transaction_identifier=str(uuid.uuid4()),
                    amount=amount.amount,
                    transaction_type="credit",
                    payment_method="wallet",
                    status="success",
                    description=f"System hold for booking with student {user.username}",
                    metadata_info={"session_booking": str(teacher.id)},
                )

                booking = SessionBooking.objects.create(
                    student=user.student_profile if hasattr(user, "student_profile") else None,
                    teacher=teacher,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    cost=total_cost,
                    is_allowed=True,
                    course=course,
                )

        else:
            booking = serializer.save()

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

        if attended_flag is True and not booking.attended:
            if user.is_staff or hasattr(user, "teacher_profile"):
                system_wallet = Wallet.objects.filter(account_type="system").first()
                if not system_wallet:
                    return Response(
                        {"detail": "System wallet not found."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                teacher_wallet = booking.teacher.user.wallet
                amount_money = Money(booking.cost, "KES")

                with transaction.atomic():
                    if system_wallet.balance < amount_money:
                        return Response(
                            {"detail": "System wallet has insufficient funds."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                    system_wallet.balance -= amount_money
                    teacher_wallet.balance += amount_money

                    system_wallet.save()
                    teacher_wallet.save()

                    teacher_tx = self._log_transaction(
                        teacher_wallet,
                        amount_money.amount,
                        "credit",
                        f"Payment for attended session with student {booking.student.user.username}",
                    )
                    self._log_transaction(
                        system_wallet,
                        -amount_money.amount,
                        "debit",
                        f"System payout to {booking.teacher.user.username}",
                        related_tx=teacher_tx,
                    )

                    booking.attended = True
                    booking.status = "completed"
                    booking.save()

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

            if booking.scheduled_start - timezone.now() <= timedelta(minutes=30):
                return Response(
                    {"detail": "Rescheduling allowed only 30 minutes before start."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_start = request.data.get("scheduled_start")
            if not new_start:
                return Response({"detail": "New start time required."}, status=status.HTTP_400_BAD_REQUEST)

            student_wallet = booking.student.user.wallet
            system_wallet = Wallet.objects.filter(account_type="system").first()
            teacher = booking.teacher
            teacher_rate = float(teacher.hourly_rate.amount)

            with transaction.atomic():
                booking_cost_money = Money(booking.cost, "KES")
                if system_wallet.balance < booking_cost_money:
                    return Response(
                        {"detail": "System wallet has insufficient funds for refund."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                system_wallet.balance -= booking_cost_money
                student_wallet.balance += booking_cost_money
                system_wallet.save()
                student_wallet.save()

                self._log_transaction(
                    student_wallet,
                    booking_cost_money.amount,
                    "refund",
                    f"Refund for rescheduled session with {teacher.user.username}",
                )

                new_start_dt = datetime.fromisoformat(new_start)
                duration_hours = float(booking.duration_hours)
                new_end = new_start_dt + timedelta(hours=duration_hours)
                total_cost = Decimal(duration_hours * teacher_rate)
                total_cost_money = Money(total_cost, "KES")

                if student_wallet.balance < total_cost_money:
                    transaction.set_rollback(True)
                    return Response(
                        {"detail": "Insufficient wallet balance to reschedule."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                student_wallet.balance -= total_cost_money
                system_wallet.balance += total_cost_money
                student_wallet.save()
                system_wallet.save()

                self._log_transaction(
                    student_wallet,
                    -total_cost_money.amount,
                    "payment",
                    f"Payment for rescheduled session with {teacher.user.username}",
                )
                self._log_transaction(
                    system_wallet,
                    total_cost_money.amount,
                    "hold",
                    f"System hold for rescheduled session {booking.id}",
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
    permission_classes = [permissions.IsAuthenticated,IsVerified]
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
