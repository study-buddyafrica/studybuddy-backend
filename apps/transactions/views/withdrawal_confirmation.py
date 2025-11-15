from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from djmoney.money import Money
from apps.transactions.models import Transaction, Wallet
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name="dispatch")
class IntaSendWithdrawalWebhook(APIView):
    """
    Handles IntaSend webhook events for withdrawals.
    """

    def post(self, request, *args, **kwargs):
        data = request.data
        state = data.get("state")
        intasend_tx_id = None

        # IntaSend sends 'transactions' array in payload
        transactions = data.get("transactions", [])
        if transactions and len(transactions) > 0:
            intasend_tx_id = transactions[0].get("transaction_id")

        if not intasend_tx_id:
            logger.error(f"Webhook missing transaction_id: {data}")
            return Response({"error": "transaction_id not found"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch transaction in DB
        tx = Transaction.objects.filter(transaction_identifier=intasend_tx_id).first()
        if not tx:
            logger.warning(f"Webhook transaction not found in DB: {intasend_tx_id}")
            return Response({"error": "transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        # Save webhook raw data
        metadata = tx.metadata_info or {}
        metadata["intasend_webhook"] = data

        # Map IntaSend state to local status
        state_map = {
            "FAILED": "failed",
            "CANCELLED": "failed",
            "PROCESSING": "processing",
            "PENDING": "processing",
            "COMPLETE": "completed",
        }
        tx_status = state_map.get(state, None)
        if not tx_status:
            logger.error(f"Unknown webhook state: {state}")
            return Response({"error": "unknown state"}, status=status.HTTP_400_BAD_REQUEST)

        # Process balances inside DB transaction
        with db_transaction.atomic():
            if tx_status == "completed" and tx.transaction_type == "withdrawal":
                # Update system wallet balance based on IntaSend wallet
                try:
                    system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)

                    # Optional: sync with IntaSend current balance if available
                    wallet_info = data.get("wallet", {})
                    available_balance = wallet_info.get("available_balance")
                    if available_balance:
                        system_wallet.balance = Money(Decimal(available_balance), "KES")
                    system_wallet.save(update_fields=["balance"])

                except Exception as e:
                    logger.error(f"Error updating system wallet: {e}")

            elif tx_status == "failed" and tx.transaction_type == "withdrawal":
                # Refund user wallet
                wallet = tx.wallet
                wallet.balance += tx.amount
                wallet.save(update_fields=["balance"])

            # Save final transaction status
            tx.status = tx_status
            tx.metadata_info = metadata
            tx.save(update_fields=["status", "metadata_info"])

        return Response({"status": tx.status}, status=status.HTTP_200_OK)
