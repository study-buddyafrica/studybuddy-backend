"""PaystackPaymentView — initiates a Paystack checkout session."""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.transactions.services.payment_service import PaymentService, PaystackAPIError


class PaystackPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        amount = data.get("amount")
        currency = data.get("currency", "KES")
        transaction_type = data.get("transaction_type", "course_payment")
        reference_id = data.get("reference_id", "")

        service = PaymentService()
        try:
            result = service.initiate_checkout(
                user=request.user,
                amount=amount,
                currency=currency,
                transaction_type=transaction_type,
                reference_id=reference_id,
            )
        except ValidationError:
            raise
        except PaystackAPIError as exc:
            return Response(
                {"error": "Payment gateway error", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result, status=status.HTTP_201_CREATED)
