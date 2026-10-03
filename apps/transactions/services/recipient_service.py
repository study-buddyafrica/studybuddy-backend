"""Paystack transfer-recipient creation for teacher payouts."""
from __future__ import annotations

import requests
from django.conf import settings


class PaystackRecipientError(Exception):
    """Raised when Paystack cannot create a transfer recipient."""


class PaystackRecipientService:
    CREATE_URL = "https://api.paystack.co/transferrecipient"

    def create_recipient(
        self,
        *,
        name: str,
        account_number: str,
        bank_code: str,
        currency: str = "KES",
        recipient_type: str = "nuban",
    ) -> str:
        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if not secret_key:
            raise PaystackRecipientError("Paystack is not configured.")

        payload = {
            "type": recipient_type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency,
        }
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.CREATE_URL, json=payload, headers=headers, timeout=15
            )
            response_data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PaystackRecipientError(
                "Unable to reach Paystack while creating the recipient."
            ) from exc

        if not response_data.get("status"):
            raise PaystackRecipientError(
                response_data.get("message", "Paystack rejected the recipient.")
            )

        recipient_code = response_data.get("data", {}).get("recipient_code")
        if not recipient_code:
            raise PaystackRecipientError(
                "Paystack returned no recipient code."
            )
        return recipient_code
