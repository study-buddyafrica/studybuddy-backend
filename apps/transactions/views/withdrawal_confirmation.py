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
    Unified webhook for deposits and withdrawals.
    Withdrawals: update system wallet and track payout.
    Deposits: credit user wallet.
    Syncs system wallet balance with IntaSend available_balance.
    """

    def post(self, request, *args, **kwargs):
        data = request.data
        logger.info(f"Received IntaSend webhook: {data}")

        # Identify transaction
        tx = None
        transaction_identifier = data.get("transaction_id")
        api_ref = data.get("api_ref")

        if transaction_identifier:
            # Likely a withdrawal
            tx = Transaction.objects.filter(transaction_identifier=transaction_identifier).first()
        elif api_ref:
            # Likely a deposit
            tx = Transaction.objects.filter(metadata_info__api_ref=api_ref).first()

        if not tx:
            logger.warning("Transaction not found for webhook.")
            return Response({"error": "transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        # Save raw webhook for audit
        metadata = tx.metadata_info or {}
        metadata["intasend_webhook"] = data
        tx.metadata_info = metadata

        # State mapping
        state_map = {
            # Withdrawals
            "Preview and Approve": "pending",
            "Confirming balance": "processing",
            "Processing (FLT)": "processing",
            "Failed Processing": "failed",
            "Processing (FLTRSLT)": "processing",
            "Sending payment": "processing",
            "Processing payment": "processing",
            "Completed": "completed",
            # Deposits
            "PENDING": "processing",
            "FAILED": "failed",
            "CANCELLED": "failed",
            "SUCCESSFUL": "completed",
        }

        # Determine state
        if tx.transaction_type == "withdrawal":
            tx_data = data.get("transactions", [{}])[0]
            state = tx_data.get("status", data.get("status"))
        else:
            state = data.get("status")

        tx.status = state_map.get(state)
        if not tx.status:
            logger.error(f"Unknown state from IntaSend: {state}")
            return Response({"error": "unknown state"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with db_transaction.atomic():
                # Handle deposits
                if tx.transaction_type == "deposit":
                    if tx.status == "completed":
                        user_wallet = tx.wallet
                        amount = Decimal(data.get("amount") or tx.amount.amount)
                        user_wallet.balance += Money(amount, tx.amount_currency or "KES")
                        user_wallet.save(update_fields=["balance"])
                        tx.metadata_info["credited_amount"] = float(amount)
                        logger.info(f"Deposit completed: credited {amount} to {tx.wallet.user.email}")

                # Handle withdrawals
                elif tx.transaction_type == "withdrawal":
                    system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)
                    payout_amount = Decimal(tx.metadata_info.get("payout_amount", 0))
                    intasend_fee = Decimal(tx.metadata_info.get("intasend_fee", 0))
                    total_deduction = payout_amount + intasend_fee

                    if tx.status == "completed":
                        # Deduct from system wallet the total payout + fee
                        system_wallet.balance -= Money(total_deduction, "KES")

                        # Sync with IntaSend available balance if provided
                        intasend_wallet = data.get("wallet", {})
                        available_balance = intasend_wallet.get("available_balance")
                        if available_balance:
                            try:
                                available_balance = Decimal(available_balance)
                                system_wallet.balance = Money(available_balance, "KES")
                                tx.metadata_info["system_wallet_synced"] = True
                                logger.info(f"System wallet synced to IntaSend available balance: {available_balance}")
                            except Exception:
                                logger.warning("Failed to parse IntaSend available_balance")

                        system_wallet.save(update_fields=["balance"])
                        tx.metadata_info["system_wallet_updated"] = True
                        logger.info(f"Withdrawal completed: deducted {total_deduction} from system wallet")

                    elif tx.status == "failed":
                        # Refund user wallet
                        user_wallet = tx.wallet
                        amount = tx.amount.amount
                        user_wallet.balance += Money(amount, tx.amount_currency or "KES")
                        user_wallet.save(update_fields=["balance"])
                        tx.metadata_info["refunded_amount"] = float(amount)
                        logger.info(f"Withdrawal failed: refunded {amount} to {tx.wallet.user.email}")

                tx.save()
                return Response({"status": tx.status}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error processing IntaSend webhook for tx {tx.id}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
