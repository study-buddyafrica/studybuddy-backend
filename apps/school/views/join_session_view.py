from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from moneyed import Money

from apps.core.permissions import IsStudent, IsVerified
from apps.school.models import LiveSession, SessionBooking
from apps.transactions.models import Wallet, Transaction
from apps.school.serializers.livesession_serializer import LiveSessionSerializer
import uuid


class StudentJoinLiveSessionView(generics.GenericAPIView):
    serializer_class = LiveSessionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsStudent,
        IsVerified,
    ]

    def post(self, request, session_booking_id):
        user = request.user

        try:
            booking = SessionBooking.objects.select_related("student", "teacher").get(
                id=session_booking_id, student__user=user
            )
        except SessionBooking.DoesNotExist:
            return Response(
                {"detail": "No session found for this student."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            live_session = LiveSession.objects.get(session=booking)
        except LiveSession.DoesNotExist:
            return Response(
                {"detail": "Live session not created yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.attended:
            return Response(
                {"detail": "Session already marked as attended."},
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            system_wallet, _ = Wallet.objects.select_for_update().get_or_create(
                account_type="system",
                defaults={"balance": Money(0, "KES"), "is_active": True},
            )
            teacher_wallet, _ = Wallet.objects.select_for_update().get_or_create(
                user=booking.teacher.user,
                defaults={"balance": Money(0, "KES"), "account_type": "teacher"},
            )

            amount = booking.cost
            if not isinstance(amount, Money):
                amount = Money(amount, "KES")

            if system_wallet.balance < amount:
                return Response(
                    {"detail": "System wallet has insufficient funds for payout."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            system_wallet.balance -= amount
            teacher_wallet.balance += amount

            system_wallet.save(update_fields=["balance"])
            teacher_wallet.save(update_fields=["balance"])

            booking.attended = True
            booking.status = "completed"
            booking.save(update_fields=["attended", "status"])

            live_session.ended_at = timezone.now()
            live_session.save(update_fields=["ended_at"])

            Transaction.objects.create(
                wallet=system_wallet,
                transaction_identifier=str(uuid.uuid4()),
                amount=-amount.amount,
                transaction_type="transfer",
                payment_method="internal",
                status="success",
                description=f"Transferred funds to {booking.teacher.user.username} for session {booking.id}",
                metadata_info={"session_booking_id": str(booking.id)},
            )

            Transaction.objects.create(
                wallet=teacher_wallet,
                transaction_identifier=str(uuid.uuid4()),
                amount=amount.amount,
                transaction_type="credit",
                payment_method="wallet",
                status="success",
                description=f"Credit for session with {booking.student.user.username}",
                metadata_info={"session_booking_id": str(booking.id)},
            )

        serializer = LiveSessionSerializer(live_session, context={"request": request})
        return Response(
            {
                "detail": "Teacher credited and session marked as attended.",
                "session": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
