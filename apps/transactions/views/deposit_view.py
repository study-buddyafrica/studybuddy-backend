import uuid
from decimal import Decimal
from django.urls import reverse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from intasend import APIService
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers

from apps.transactions.models import Wallet, Transaction
from apps.core.permissions import IsVerified


class DepositAPIView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def _calculate_checkout_amount(self, amount):
        """Calculate total checkout amount including IntaSend fees."""
        amount = Decimal(amount)

        if amount <= 0:
            raise ValueError("Amount must be greater than 0")

        if amount < 100:
            fee = Decimal("2.00")
        elif amount < 500:
            fee = Decimal("4.00")
        else:
            fee = Decimal("5.00")

        checkout_amount = amount + fee
        return checkout_amount, fee

    def _get_fee_structure(self):
        """Return the fee structure for transparency."""
        return {
            "fee_structure": [
                {"range": "Below 100 KES", "fee": "2 KES"},
                {"range": "100 KES - 499 KES", "fee": "4 KES"},
                {"range": "500 KES and above", "fee": "5 KES"},
            ],
            "note": "Fees are added to ensure you receive the exact amount deposited",
        }

    @extend_schema(
        request=inline_serializer(
            name="DepositRequest",
            fields={
                "amount": serializers.DecimalField(max_digits=10, decimal_places=2)
            },
        ),
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT),
            400: OpenApiResponse(response=OpenApiTypes.OBJECT),
            500: OpenApiResponse(response=OpenApiTypes.OBJECT),
        },
    )
    def post(self, request):
        try:
            amount = Decimal(request.data.get("amount", 0))
            if amount <= 0:
                return Response(
                    {"error": "Amount must be greater than 0."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = request.user
            wallet, _ = Wallet.objects.get_or_create(user=user)

            checkout_amount, fee_amount = self._calculate_checkout_amount(amount)

            client = APIService(
                token=settings.INTASEND_SECRET_KEY.strip(),
                publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
                test=True,
            )

            webhook_url = request.build_absolute_uri(reverse("intasend-webhook"))
            redirect_url = request.build_absolute_uri(reverse("deposit-success"))
            api_ref = f"deposit_{user.id}_{uuid.uuid4().hex[:8]}"

            checkout_data = {
                "amount": float(checkout_amount),
                "currency": "KES",
                "email": user.email,
                "first_name": user.first_name or " ",
                "last_name": user.last_name or "",
                "hosted": True,
                "redirect_url": redirect_url,
                "callback_url": webhook_url,
                "api_ref": api_ref,
            }

            response = client.collect.checkout(**checkout_data)

            transaction = Transaction.objects.create(
                wallet=wallet,
                transaction_identifier=api_ref,
                amount=amount,
                transaction_type="deposit",
                payment_method="intasend",
                status="pending",
                description=f"Deposit initiated - {user.email}",
                metadata_info={
                    "checkout_data": checkout_data,
                    "intasend_response": response,
                    "fee_details": {
                        "original_amount": float(amount),
                        "fee_amount": float(fee_amount),
                        "checkout_amount": float(checkout_amount),
                        "fee_structure": self._get_fee_structure(),
                    },
                    "user_pays": float(checkout_amount),
                    "user_gets": float(amount),
                },
            )

            return Response(
                {
                    "message": "Deposit initiated successfully.",
                    "checkout_url": response.get("url"),
                    "transaction_id": str(transaction.id),
                    "api_ref": api_ref,
                    "amount_details": {
                        "original_amount": float(amount),
                        "fee_amount": float(fee_amount),
                        "total_checkout_amount": float(checkout_amount),
                        "you_pay": float(checkout_amount),
                        "you_get": float(amount),
                    },
                    "fee_breakdown": self._get_fee_structure(),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to initiate deposit: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
