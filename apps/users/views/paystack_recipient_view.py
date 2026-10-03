from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.transactions.services.recipient_service import (
    PaystackRecipientError,
    PaystackRecipientService,
)
from apps.users.serializers.paystack_recipient_serializer import (
    PaystackRecipientSerializer,
)


class PaystackRecipientView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        teacher = getattr(request.user, "teacher_profile", None)
        if teacher is None:
            return Response(
                {"detail": "Only teachers can create payout recipients."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not teacher.is_verified:
            return Response(
                {"detail": "Teacher verification is required before payouts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if teacher.paystack_recipient_code:
            return Response(
                {"recipient_code": teacher.paystack_recipient_code},
                status=status.HTTP_200_OK,
            )

        serializer = PaystackRecipientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        name = f"{request.user.first_name} {request.user.last_name}".strip()
        if not name:
            name = request.user.username

        try:
            recipient_code = PaystackRecipientService().create_recipient(
                name=name,
                account_number=data["account_number"],
                bank_code=data["bank_code"],
                currency=data["currency"],
                recipient_type=data["recipient_type"],
            )
        except PaystackRecipientError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        teacher.paystack_recipient_code = recipient_code
        teacher.save(update_fields=["paystack_recipient_code"])
        return Response(
            {"recipient_code": recipient_code},
            status=status.HTTP_201_CREATED,
        )
