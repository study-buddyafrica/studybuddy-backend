from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsVerified
from apps.transactions.services.payment_service import PaymentService, PaystackAPIError


class DepositAPIView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        amount = request.data.get("amount", 0)

        try:
            result = PaymentService().initiate_checkout(
                user=request.user,
                amount=amount,
                currency="KES",
                transaction_type="deposit",
                reference_id="",
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        except PaystackAPIError as exc:
            return Response(
                {"error": "Payment gateway error", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"message": "Deposit initiated successfully.", **result},
            status=status.HTTP_201_CREATED,
        )
