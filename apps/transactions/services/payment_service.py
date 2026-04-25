"""PaymentService — initiates Paystack checkout and records pending transactions."""
from __future__ import annotations

import uuid
import logging
import requests
from django.conf import settings
from django.db import transaction as db_transaction
from rest_framework.exceptions import ValidationError

from apps.transactions.models import Transaction, Wallet

logger = logging.getLogger(__name__)


class PaystackAPIError(Exception):
    """Raised when the Paystack API returns an error response."""


class PaymentService:
    PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"

    def initiate_checkout(
        self,
        user,
        amount,
        currency: str,
        transaction_type: str,
        reference_id,
    ) -> dict:
        """
        Validates amount, calls Paystack Initialize Transaction API,
        creates a pending Transaction, and returns checkout details.

        Returns:
            {"checkout_url": str, "transaction_id": UUID, "reference": str}

        Raises:
            ValidationError: if amount <= 0
            PaystackAPIError: if Paystack API returns an error
        """
        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            raise ValidationError({"amount": "Amount must be a valid number."})

        if amount_value <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})

        reference = f"SB_{uuid.uuid4().hex}"

        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": user.email,
            "amount": int(amount_value * 100),  # Paystack expects kobo/cents
            "currency": currency,
            "reference": reference,
            "metadata": {
                "transaction_type": transaction_type,
                "reference_id": str(reference_id),
                "user_id": str(user.id),
            },
        }

        try:
            response = requests.post(
                self.PAYSTACK_INIT_URL, json=payload, headers=headers, timeout=10
            )
            response_data = response.json()
        except requests.RequestException as exc:
            logger.error("Paystack API request failed: %s", exc)
            raise PaystackAPIError(str(exc)) from exc

        if not response_data.get("status"):
            message = response_data.get("message", "Unknown Paystack error")
            logger.error("Paystack init failed: %s | ref=%s", message, reference)
            raise PaystackAPIError(message)

        checkout_url = response_data["data"]["authorization_url"]

        wallet = getattr(user, "wallet", None)
        pending_tx = self._create_pending_transaction(
            wallet=wallet,
            amount=amount_value,
            currency=currency,
            payment_method="paystack",
            transaction_type=transaction_type,
            reference=reference,
        )

        return {
            "checkout_url": checkout_url,
            "transaction_id": pending_tx.id,
            "reference": reference,
        }

    @staticmethod
    def _create_pending_transaction(
        wallet: Wallet | None,
        amount: float,
        currency: str,
        payment_method: str,
        transaction_type: str,
        reference: str,
    ) -> Transaction:
        """Atomically creates a pending Transaction record."""
        with db_transaction.atomic():
            return Transaction.objects.create(
                wallet=wallet,
                transaction_identifier=reference,
                amount=amount,
                transaction_type=transaction_type,
                payment_method=payment_method,
                status="pending",
                metadata_info={"currency": currency},
            )
