from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from moneyed import Money

from apps.users.permissions import IsStudent
from apps.school.models import LiveSession, SessionBooking
from apps.transactions.models import Wallet, Transaction
from apps.school.serializers.livesession_serializer import LiveSessionSerializer
import uuid

class StudentJoinLiveSessionView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request, pk):
        user = request.user

        try:
            booking = SessionBooking.objects.select_related("student", "teacher").get(
                id=pk,
                student__user=user
            )
        except SessionBooking.DoesNotExist:
            return Response(
                {"detail": "No session found for this student."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            live_session = LiveSession.objects.get(session=booking)
        except LiveSession.DoesNotExist:
            return Response(
                {"detail": "Live session not created yet."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if booking.attended:
            return Response(
                {"detail": "Session already marked as attended."},
                status=status.HTTP_200_OK
            )
        
        with transaction.atomic():
            student_wallet, _ = Wallet.objects.select_for_update().get_or_create(
                user=booking.student.user,
                defaults={"balance": Money(0, "KES")}
            )
            teacher_wallet, _ = Wallet.objects.select_for_update().get_or_create(
                user=booking.teacher.user,
                defaults={"balance": Money(0, "KES")}
            )

            amount = booking.cost
            if not isinstance(amount, Money):
                amount = Money(amount, "KES")

            if student_wallet.balance < amount:
                return Response(
                    {"detail": "Insufficient balance in your wallet."},
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
            
            student_wallet.balance -= amount
            teacher_wallet.balance += amount

            student_wallet.save(update_fields=["balance"])
            teacher_wallet.save(update_fields=["balance"])

            booking.attended = True
            booking.status = "completed"
            booking.save(update_fields=["attended", "status"])

            live_session.ended_at = timezone.now()
            live_session.save(update_fields=["ended_at"])

            Transaction.objects.create(
                wallet=student_wallet,
                transaction_identifier=str(uuid.uuid4()),
                amount=-amount.amount,  
                transaction_type="debit",
                payment_method="wallet",
                status="success",
                description=f"Payment for session with {booking.teacher.user.username}",
                metadata_info={"session_booking_id": str(booking.id)},
            )

            Transaction.objects.create(
                wallet=teacher_wallet,
                transaction_identifier=str(uuid.uuid4()),
                amount=amount.amount,
                transaction_type="credit",
                payment_method="wallet",
                status="success",
                description=f"Credit for attended session with {booking.student.user.username}",
                metadata_info={"session_booking_id": str(booking.id)},
            )
        serializer = LiveSessionSerializer(live_session, context={"request": request})
        return Response({
            "detail": "Session attended, payment processed, and teacher credited.",
            "session": serializer.data
        }, status=status.HTTP_200_OK)