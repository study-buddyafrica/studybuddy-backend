"""TransferService — releases escrowed funds to teachers via Paystack Transfers API."""
from __future__ import annotations

import logging
import uuid

import requests
from django.conf import settings
from django.db import transaction as db_transaction
from djmoney.money import Money

from apps.transactions.models import Transaction, EscrowWallet

logger = logging.getLogger(__name__)

PAYSTACK_TRANSFER_URL = "https://api.paystack.co/transfer"


class TransferService:
    def release_escrow(self, session_booking) -> None:
        """
        Called when SessionBooking.status transitions to 'completed'.
        Deducts platform fee, calls Paystack Transfers API, records transfer_code,
        and updates EscrowWallet.state to 'released' or 'failed'.
        """
        try:
            escrow = EscrowWallet.objects.select_for_update().get(
                session_booking=session_booking, state="held"
            )
        except EscrowWallet.DoesNotExist:
            logger.info(
                "release_escrow: no held escrow for booking %s", session_booking.id
            )
            return

        teacher = session_booking.teacher
        recipient_code = getattr(teacher, "paystack_recipient_code", None)

        if not recipient_code:
            logger.error(
                "release_escrow: teacher %s has no paystack_recipient_code; "
                "retaining escrow for booking %s",
                teacher.id,
                session_booking.id,
            )
            with db_transaction.atomic():
                escrow.state = "failed"
                escrow.save(update_fields=["state"])
            return

        payout = self._calculate_payout(escrow.amount)
        reference = f"ESC_{uuid.uuid4().hex}"

        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "source": "balance",
            "amount": int(payout.amount * 100),
            "recipient": recipient_code,
            "reference": reference,
            "reason": f"Session payout for booking {session_booking.id}",
        }

        try:
            response = requests.post(
                PAYSTACK_TRANSFER_URL, json=payload, headers=headers, timeout=15
            )
            response_data = response.json()
        except requests.RequestException as exc:
            logger.error("Paystack transfer request failed: %s", exc)
            with db_transaction.atomic():
                escrow.state = "failed"
                escrow.save(update_fields=["state"])
            return

        if not response_data.get("status"):
            error_msg = response_data.get("message", "Unknown error")
            logger.error(
                "Paystack transfer failed: %s | booking=%s", error_msg, session_booking.id
            )
            with db_transaction.atomic():
                escrow.state = "failed"
                escrow.save(update_fields=["state"])
            return

        transfer_code = response_data.get("data", {}).get("transfer_code", "")

        with db_transaction.atomic():
            release_tx = Transaction.objects.create(
                wallet=None,
                transaction_identifier=reference,
                amount=payout.amount,
                transaction_type="escrow_release",
                payment_method="paystack",
                status="pending",
                metadata_info={
                    "transfer_code": transfer_code,
                    "session_booking_id": str(session_booking.id),
                    "gross_amount": str(escrow.amount.amount),
                    "payout_amount": str(payout.amount),
                },
                related_transaction=escrow.held_transaction,
            )
            escrow.release_transaction = release_tx
            escrow.state = "released"
            escrow.save(update_fields=["release_transaction", "state"])

        logger.info(
            "Escrow released for booking %s; transfer_code=%s",
            session_booking.id,
            transfer_code,
        )

    @staticmethod
    def _calculate_payout(gross_amount: Money) -> Money:
        """gross_amount * (1 - PLATFORM_FEE_PERCENT / 100)"""
        fee_percent = getattr(settings, "PLATFORM_FEE_PERCENT", 10)
        multiplier = 1 - (float(fee_percent) / 100)
        net = gross_amount.amount * multiplier
        return Money(round(net, 2), gross_amount.currency)
