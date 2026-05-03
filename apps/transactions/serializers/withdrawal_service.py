import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from djmoney.money import Money
import requests

from apps.transactions.models import Transaction, Wallet

logger = logging.getLogger(__name__)

PAYSTACK_TRANSFER_URL = "https://api.paystack.co/transfer"


class WithdrawalService:
    @staticmethod
    @transaction.atomic
    def process_withdrawal(user, requested_amount: Decimal):
        """Process a withdrawal through Paystack and record the ledger entries."""
        wallet = Wallet.objects.select_for_update().get(user=user)
        amount_money = Money(requested_amount, "KES")
        teacher_profile = getattr(user, "teacher_profile", None)
        recipient_code = getattr(teacher_profile, "paystack_recipient_code", None)

        if requested_amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero.")

        if wallet.balance < amount_money:
            raise ValueError("Insufficient wallet balance.")

        if not recipient_code:
            raise ValueError("Paystack recipient code is required for withdrawals.")

        platform_fee_percent = Decimal(
            str(getattr(settings, "WITHDRAWAL_PLATFORM_FEE_PERCENT", "30"))
        )
        gateway_fee_percent = Decimal(
            str(getattr(settings, "PAYSTACK_TRANSFER_FEE_PERCENT", "0"))
        )
        fx_fee_percent = Decimal(str(getattr(settings, "PAYSTACK_FX_FEE_PERCENT", "0")))

        system_cut = (
            requested_amount * platform_fee_percent / Decimal("100")
        ).quantize(Decimal("0.01"))
        paystack_fee = (
            requested_amount * (gateway_fee_percent + fx_fee_percent) / Decimal("100")
        ).quantize(Decimal("0.01"))
        payout_amount = requested_amount - system_cut - paystack_fee

        if payout_amount <= 0:
            raise ValueError("Payout too small after deductions.")

        wallet.balance -= amount_money
        wallet.save(update_fields=["balance"])
        system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)
        system_wallet.balance += Money(system_cut + paystack_fee, "KES")
        system_wallet.save(update_fields=["balance"])

        tx = Transaction.objects.create(
            wallet=wallet,
            transaction_identifier=f"withdraw_{user.id}_{uuid.uuid4().hex[:12]}",
            transaction_type="withdrawal",
            amount=amount_money,
            payment_method="paystack",
            status="pending",
            description=f"Withdrawal request of {requested_amount} KES by {user.email}",
            metadata_info={
                "requested_amount": float(requested_amount),
                "system_cut": float(system_cut),
                "paystack_fee": float(paystack_fee),
                "payout_amount": float(payout_amount),
                "recipient_code": recipient_code,
            },
        )

        try:
            payout_response = WithdrawalService._send_paystack_transfer(
                user=user,
                recipient_code=recipient_code,
                payout_amount=payout_amount,
            )
            transfer_code = payout_response.get("data", {}).get("transfer_code", "")

            tx.metadata_info.update(
                {
                    "payout_response": payout_response,
                    "transfer_code": transfer_code,
                    "payout_total_deduction": float(payout_amount + paystack_fee),
                    "total_system_wallet_credit": float(system_cut + paystack_fee),
                }
            )
            tx.status = "processing"
            tx.save(update_fields=["status", "metadata_info"])

        except Exception as e:
            wallet.balance += amount_money
            wallet.save(update_fields=["balance"])

            system_wallet.balance -= Money(system_cut + paystack_fee, "KES")
            system_wallet.save(update_fields=["balance"])

            tx.status = "failed"
            tx.metadata_info.update({"error": str(e)})
            tx.save(update_fields=["status", "metadata_info"])
            logger.error(f"Withdrawal failed for {user.email}: {e}")
            raise e

        return tx

    @staticmethod
    def _send_paystack_transfer(user, recipient_code: str, payout_amount: Decimal):
        """Send the transfer request to Paystack."""
        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "source": "balance",
            "amount": int((payout_amount * Decimal("100")).quantize(Decimal("1"))),
            "recipient": recipient_code,
            "reference": f"WD_{uuid.uuid4().hex}",
            "reason": f"Withdrawal payout for {user.email}",
        }

        response = requests.post(
            PAYSTACK_TRANSFER_URL, json=payload, headers=headers, timeout=15
        )
        response_data = response.json()

        if not response_data.get("status"):
            raise ValueError(response_data.get("message", "Paystack transfer failed."))

        logger.info(
            "Sending payout %s KES to recipient %s", payout_amount, recipient_code
        )
        return response_data
