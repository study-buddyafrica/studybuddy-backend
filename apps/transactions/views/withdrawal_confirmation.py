import logging
import secrets
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from djmoney.money import Money
from django.conf import settings
from apps.transactions.models import Transaction, Wallet

logger = logging.getLogger(__name__)

STATE_MAP = {
    # Withdrawal states
    "Preview and Approve": "processing",
    "Confirming balance": "processing",
    "Processing (FLT)": "processing",
    "Failed Processing": "failed",
    "Processing (FLTRSLT)": "processing",
    "Sending payment": "processing",
    "Processing payment": "processing",
    "Completed": "completed",
    # Deposit states
    "FAILED": "failed",
    "CANCELLED": "failed",
    "PENDING": "processing",
    "COMPLETE": "completed",
}


@method_decorator(csrf_exempt, name="dispatch")
class IntaSendWebhookView(APIView):
    def _is_valid_webhook(self, request):
        """Validate shared-secret challenge for webhook authenticity."""
        expected = getattr(settings, "INTASEND_WEBHOOK_CHALLENGE", None)
        if not expected:
            return False

        provided = (
            request.headers.get("X-IntaSend-Challenge")
            or request.headers.get("X-Webhook-Challenge")
            or request.data.get("challenge")
        )
        if not provided:
            return False

        return secrets.compare_digest(str(provided), str(expected))

    def post(self, request, *args, **kwargs):
        if not self._is_valid_webhook(request):
            logger.warning("Rejected webhook: invalid challenge")
            return Response({"error": "invalid webhook signature"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data

        tx = None

        # 1️⃣ Try to find deposit transaction by api_ref
        api_ref = data.get("api_ref")
        if api_ref:
            tx = Transaction.objects.filter(metadata_info__api_ref=api_ref).first()

        # 2️⃣ If not found, try withdrawal transaction by transaction_id from first transaction
        if not tx:
            transactions = data.get("transactions", [])
            if transactions:
                transaction_id = transactions[0].get("transaction_id")
                if transaction_id:
                    tx = Transaction.objects.filter(transaction_identifier=transaction_id).first()

        if not tx:
            logger.warning(f"Transaction not found in DB for webhook: {data}")
            return Response({"error": "transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        # 3️⃣ Determine the state
        # Use batch-level status for deposits or withdrawals
        webhook_status = data.get("status") or transactions[0].get("status")
        mapped_status = STATE_MAP.get(webhook_status)
        if not mapped_status:
            logger.warning(f"Unknown webhook state '{webhook_status}' for transaction {tx.id}")
            return Response({"error": f"Unknown state '{webhook_status}'"}, status=status.HTTP_400_BAD_REQUEST)

        # 4️⃣ Update metadata with webhook payload
        tx.metadata_info["intasend_webhook"] = data

        # 5️⃣ Begin atomic transaction
        with db_transaction.atomic():
            # Update status
            tx.status = mapped_status

            # 6️⃣ Handle completed withdrawals
            if tx.transaction_type == "withdrawal" and mapped_status == "completed":
                # Nothing to credit user wallet (amount already deducted)
                # Update system wallet to reflect actual balance (from IntaSend wallet)
                intasend_wallet_balance = data.get("wallet", {}).get("current_balance")
                if intasend_wallet_balance is not None:
                    system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)
                    system_wallet.balance = Money(Decimal(intasend_wallet_balance), "KES")
                    system_wallet.save(update_fields=["balance"])
                    logger.info(f"System wallet updated to {intasend_wallet_balance} KES for withdrawal {tx.id}")

            # 7️⃣ Handle completed deposits
            elif tx.transaction_type == "deposit" and mapped_status == "completed":
                # Credit user wallet
                deposit_amount = transactions[0].get("amount") if transactions else tx.amount.amount
                wallet = tx.wallet
                wallet.balance += Money(Decimal(deposit_amount), "KES")
                wallet.save(update_fields=["balance"])
                tx.metadata_info["credited_amount"] = float(deposit_amount)
                logger.info(f"User wallet credited with {deposit_amount} KES for deposit {tx.id}")

            # 8️⃣ Retry logic for failed or processing transactions (optional)
            elif mapped_status in ["processing", "failed"]:
                tx.metadata_info.setdefault("retry_count", 0)
                tx.metadata_info["retry_count"] += 1
                # Here you could queue a background job to retry after some time
                logger.info(f"Transaction {tx.id} in {mapped_status} state. Retry count: {tx.metadata_info['retry_count']}")

            tx.save()

        return Response({"status": tx.status, "transaction_id": str(tx.id)}, status=status.HTTP_200_OK)
