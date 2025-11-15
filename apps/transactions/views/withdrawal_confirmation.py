import logging
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from djmoney.money import Money
from apps.transactions.models import Transaction, Wallet

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class IntaSendWebhookView(APIView):
    """
    Unified webhook to handle both deposits and withdrawals from IntaSend.
    """

    def post(self, request, *args, **kwargs):
        data = request.data
        logger.info(f"IntaSend webhook received: {data}")

        # Determine if this is a withdrawal or deposit
        transactions = data.get("transactions", [])
        transaction_id = transactions[0]["transaction_id"] if transactions else None
        api_ref = data.get("api_ref")

        # Lookup transaction in DB
        tx = None
        if transaction_id:
            tx = Transaction.objects.filter(transaction_identifier=transaction_id).first()
        if not tx and api_ref:
            tx = Transaction.objects.filter(metadata_info__intasend_response__api_ref=api_ref).first()

        if not tx:
            logger.warning(f"Webhook transaction not found. transaction_id={transaction_id}, api_ref={api_ref}")
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        # Update metadata with webhook payload
        tx.metadata_info["webhook_update"] = data

        # Map IntaSend state to internal status
        state = data.get("state")
        state_map = {
            "FAILED": "failed",
            "CANCELLED": "failed",
            "PROCESSING": "processing",
            "PENDING": "processing",
            "COMPLETE": "completed",
        }

        tx_status = state_map.get(state)
        if not tx_status:
            logger.error(f"Unknown state in webhook: {state}")
            return Response({"error": "Unknown state"}, status=status.HTTP_400_BAD_REQUEST)

        tx.status = tx_status

        # Handle withdrawals
        if tx_status == "completed" and transaction_id:
            try:
                with db_transaction.atomic():
                    metadata = tx.metadata_info or {}
                    payout_amount = metadata.get("payout_amount") or float(tx.amount.amount)
                    
                    # Deduct from system wallet (IntaSend already took the fee)
                    system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)
                    # Update system wallet with IntaSend’s current available balance
                    if "wallet" in data:
                        system_balance = data["wallet"].get("available_balance")
                        if system_balance is not None:
                            system_wallet.balance = Money(Decimal(system_balance), system_wallet.balance.currency)
                            system_wallet.save(update_fields=["balance"])
                    
                    # Payout already sent to user, so nothing to credit user again

            except Exception as e:
                logger.error(f"Error updating system wallet after withdrawal: {e}")
                tx.status = "failed"

        # Handle deposits
        elif tx_status == "completed" and api_ref:
            try:
                with db_transaction.atomic():
                    # Get deposit amount from webhook
                    deposit_amount = None
                    if transactions and len(transactions) > 0:
                        deposit_amount = Decimal(transactions[0].get("amount", "0"))
                    
                    if deposit_amount:
                        tx.wallet.balance += Money(deposit_amount, tx.wallet.balance.currency)
                        tx.wallet.save(update_fields=["balance"])
                        tx.metadata_info["credited_amount"] = float(deposit_amount)

            except Exception as e:
                logger.error(f"Error crediting user wallet for deposit: {e}")
                tx.status = "failed"

        tx.save()
        logger.info(f"Transaction {tx.transaction_identifier} updated via webhook. Status: {tx.status}")

        return Response({"status": tx.status}, status=status.HTTP_200_OK)
