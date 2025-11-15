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
    Unified IntaSend webhook handler for both deposits and withdrawals.
    """
    def post(self, request, *args, **kwargs):
        data = request.data
        logger.info(f"IntaSend webhook received: {data}")

        transactions = data.get("transactions", [])
        if not transactions:
            return Response({"error": "No transactions in payload"}, status=status.HTTP_400_BAD_REQUEST)

        transaction_id = transactions[0].get("transaction_id")
        api_ref = data.get("api_ref")

        tx = None
        if transaction_id:
            tx = Transaction.objects.filter(transaction_identifier=transaction_id).first()
        if not tx and api_ref:
            tx = Transaction.objects.filter(metadata_info__intasend_response__api_ref=api_ref).first()
        if not tx:
            logger.warning(f"No transaction found for transaction_id={transaction_id}, api_ref={api_ref}")
            return Response({"error": "transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        # Store webhook payload
        tx.metadata_info = tx.metadata_info or {}
        tx.metadata_info["intasend_webhook"] = data

        # Determine state
        state = data.get("status") or data.get("state") or transactions[0].get("status")
        state_map = {
            # Failed states
            "FAILED": "failed",
            "CANCELLED": "failed",
            "Failed Processing": "failed",

            # Processing / intermediate
            "Preview and Approve": "processing",
            "Confirming balance": "processing",
            "Processing (FLT)": "processing",
            "Processing (FLTRSLT)": "processing",
            "Sending payment": "processing",
            "Processing payment": "processing",
            "PENDING": "processing",

            # Completed
            "Completed": "completed",
        }

        internal_status = state_map.get(state)
        if not internal_status:
            logger.error(f"Unknown IntaSend state: {state}")
            return Response({"error": f"Unknown state '{state}'"}, status=status.HTTP_400_BAD_REQUEST)

        tx.status = internal_status

        # Atomic update on success
        if internal_status == "completed":
            with db_transaction.atomic():
                wallet = tx.wallet
                metadata = tx.metadata_info or {}

                if tx.transaction_type == "withdrawal":
                    try:
                        payout_amount = Decimal(transactions[0].get("amount"))
                        fee = Decimal(transactions[0].get("charge", 0))
                        requested_amount = tx.amount.amount
                        system_cut = requested_amount * Decimal("0.30")
                    except Exception as e:
                        logger.error(f"Failed parsing withdrawal amounts: {e}")
                        return Response({"error": "Invalid transaction amounts"}, status=status.HTTP_400_BAD_REQUEST)

                    # User wallet already deducted on withdrawal request
                    system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)
                    # Update system wallet (revenue + intasend fee)
                    system_wallet.balance += Money(system_cut + fee, "KES")
                    system_wallet.save(update_fields=["balance"])

                    metadata["user_gets"] = float(payout_amount)
                    metadata["intasend_fee"] = float(fee)
                    metadata["total_system_wallet_credit"] = float(system_cut + fee)
                    metadata["intasend_total_deduction"] = float(payout_amount + fee)
                    metadata["payout_completed"] = True

                elif tx.transaction_type == "deposit":
                    try:
                        deposit_amount = Decimal(transactions[0].get("amount"))
                    except Exception:
                        deposit_amount = tx.amount.amount

                    wallet.balance += Money(deposit_amount, "KES")
                    wallet.save(update_fields=["balance"])
                    metadata["credited_amount"] = float(deposit_amount)

                tx.metadata_info = metadata
                tx.save(update_fields=["status", "metadata_info"])
        else:
            tx.save(update_fields=["status", "metadata_info"])

        return Response({"status": tx.status}, status=status.HTTP_200_OK)
