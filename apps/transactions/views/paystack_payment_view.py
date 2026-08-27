"""PaystackPaymentView — initiates a Paystack checkout session."""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import OpenApiResponse, inline_serializer, extend_schema
from rest_framework import serializers

from apps.transactions.services.payment_service import PaymentService, PaystackAPIError


class PaystackPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Initialize a Paystack checkout",
        request=inline_serializer(
            name="PaystackCheckoutRequest",
            fields={
                "amount": serializers.DecimalField(max_digits=12, decimal_places=2),
                "currency": serializers.CharField(required=False, default="KES"),
                "transaction_type": serializers.CharField(
                    required=False, default="course_payment"
                ),
                "reference_id": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={
            201: OpenApiResponse(description="Paystack checkout initialized"),
            400: OpenApiResponse(description="Invalid payment data"),
            502: OpenApiResponse(description="Paystack gateway error"),
        },
    )
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
