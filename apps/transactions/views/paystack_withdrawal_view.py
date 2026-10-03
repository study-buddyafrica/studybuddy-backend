"""PaystackWithdrawalView — processes teacher M-Pesa withdrawals via Paystack Transfers."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction as db_transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from djmoney.money import Money

from apps.transactions.models import Transaction, Wallet
from apps.core.permissions import IsVerified

logger = logging.getLogger(__name__)

PAYSTACK_TRANSFER_URL = "https://api.paystack.co/transfer"


class PaystackWithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class PaystackWithdrawalView(APIView):
    """Teacher withdrawal to M-Pesa via Paystack Transfers API."""

    permission_classes = [IsAuthenticated, IsVerified]

    @extend_schema(
        summary="Initiate teacher withdrawal to M-Pesa via Paystack",
        request=PaystackWithdrawalSerializer,
        responses={
            200: OpenApiResponse(description="Withdrawal initiated successfully"),
            400: OpenApiResponse(description="Invalid request or insufficient funds"),
            403: OpenApiResponse(description="Teacher not verified or no recipient configured"),
            502: OpenApiResponse(description="Paystack gateway error"),
        },
    )
    def post(self, request):
        serializer = PaystackWithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        # Verify user is a verified teacher
        teacher = getattr(request.user, "teacher_profile", None)
        if teacher is None:
            return Response(
                {"detail": "Only teachers can initiate withdrawals."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not teacher.is_verified:
            return Response(
                {"detail": "Teacher verification is required before withdrawals."},
                status=status.HTTP_403_FORBIDDEN,
            )

        recipient_code = getattr(teacher, "paystack_recipient_code", None)
        if not recipient_code:
            return Response(
                {
                    "detail": "M-Pesa payout recipient not configured. "
                    "Call POST /api/wallet/payout-recipient/ first."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate amount and debit wallet atomically
        try:
            with db_transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                amount_money = Money(amount, "KES")

                if wallet.balance < amount_money:
                    return Response(
                        {"detail": "Insufficient wallet balance."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Debit teacher wallet
                wallet.balance -= amount_money
                wallet.save(update_fields=["balance"])

                # Create pending withdrawal transaction
                reference = f"WD_{uuid.uuid4().hex[:12]}"
                withdrawal_tx = Transaction.objects.create(
                    wallet=wallet,
                    transaction_identifier=reference,
                    amount=amount_money,
                    transaction_type="withdrawal",
                    payment_method="paystack",
                    status="pending",
                    description=f"Teacher withdrawal to M-Pesa: {amount} KES",
                    metadata_info={
                        "recipient_code": recipient_code,
                        "phone_number": teacher.user.profile.phone_number
                        if hasattr(teacher.user, "profile")
                        else "N/A",
                    },
                )

        except Wallet.DoesNotExist:
            return Response(
                {"detail": "Teacher wallet not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Call Paystack Transfers API
        try:
            transfer_code = self._initiate_paystack_transfer(
                amount=amount,
                recipient_code=recipient_code,
                reference=reference,
                reason=f"StudyBuddy Teacher Withdrawal - {reference}",
            )
        except Exception as exc:
            # Rollback wallet debit on transfer failure
            with db_transaction.atomic():
                wallet.balance += amount_money
                wallet.save(update_fields=["balance"])
                withdrawal_tx.status = "failed"
                withdrawal_tx.metadata_info["error"] = str(exc)
                withdrawal_tx.save(update_fields=["status", "metadata_info"])
            logger.error("Paystack transfer failed for withdrawal %s: %s", reference, exc)
            return Response(
                {"error": "Payment gateway error", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Update transaction with transfer_code
        withdrawal_tx.metadata_info["transfer_code"] = transfer_code
        withdrawal_tx.save(update_fields=["metadata_info"])

        return Response(
            {
                "success": True,
                "message": "Withdrawal initiated successfully via Paystack M-Pesa.",
                "transfer_code": transfer_code,
                "amount": str(amount),
                "currency": "KES",
                "status": "pending",
                "transaction_id": str(withdrawal_tx.id),
            },
            status=status.HTTP_200_OK,
        )

    def _initiate_paystack_transfer(
        self,
        *,
        amount: Decimal,
        recipient_code: str,
        reference: str,
        reason: str,
    ) -> str:
        """Call Paystack Transfers API and return transfer_code."""
        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if not secret_key:
            raise RuntimeError("Paystack is not configured.")

        subunits = int(round(float(amount) * 100))  # Convert KES to cents
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "source": "balance",
            "amount": subunits,
            "recipient": recipient_code,
            "reference": reference,
            "currency": "KES",
            "reason": reason,
        }

        import requests

        try:
            response = requests.post(
                PAYSTACK_TRANSFER_URL, json=payload, headers=headers, timeout=15
            )
            response_data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"Unable to reach Paystack: {exc}") from exc

        if not response_data.get("status"):
            raise RuntimeError(
                response_data.get("message", "Paystack rejected the transfer.")
            )

        transfer_code = response_data.get("data", {}).get("transfer_code")
        if not transfer_code:
            raise RuntimeError("Paystack returned no transfer code.")

        return transfer_code