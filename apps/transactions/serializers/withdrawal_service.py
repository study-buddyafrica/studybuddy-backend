import uuid
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from djmoney.money import Money
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.transactions.models import Transaction, Wallet
from intasend import APIService

logger = logging.getLogger(__name__)

class WithdrawalService:

    @staticmethod
    @transaction.atomic
    def process_withdrawal(user, requested_amount: Decimal):
        """
        Process withdrawal using IntaSend M-Pesa transfer with dynamic fee estimation.
        """
        wallet = Wallet.objects.select_for_update().get(user=user)
        amount_money = Money(requested_amount, "KES")

        if requested_amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero.")

        # 1. Check user balance
        if wallet.balance < amount_money:
            raise ValueError("Insufficient wallet balance.")

        # 2. Compute system cut (30%)
        system_cut = requested_amount * Decimal("0.30")

        # 3. Estimate IntaSend charge via preview (or directly from SDK)
        service = APIService(
            token=settings.INTASEND_SECRET_KEY.strip(),
            publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
            test=True,  # Use False in production
        )

        # Prepare preview transaction for fee estimation
        preview_transactions = [{
            "name": user.username,
            "account": "254745897362",  # Replace with user M-Pesa number
            "amount": float(requested_amount - system_cut)
        }]

        preview_response = service.transfer.mpesa(
            currency="KES",
            transactions=preview_transactions,
            requires_approval="NO"
        )

        intasend_fee = Decimal(str(preview_response["charge_estimate"]))
        payout_amount = requested_amount - system_cut - intasend_fee

        if payout_amount <= 0:
            raise ValueError("Payout too small after deductions.")

        # 4. Deduct requested amount from user wallet
        wallet.balance -= amount_money
        wallet.save(update_fields=["balance"])

        # 5. Credit system wallet (system cut + IntaSend fee)
        system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)
        system_wallet.balance += Money(system_cut + intasend_fee, "KES")
        system_wallet.save(update_fields=["balance"])

        # 6. Create transaction record
        tx = Transaction.objects.create(
            wallet=wallet,
            transaction_identifier=f"withdraw_{user.id}_{uuid.uuid4().hex[:12]}",
            transaction_type="withdrawal",
            amount=amount_money,
            payment_method="intasend",
            status="processing",
            description=f"Withdrawal request of {requested_amount} KES by {user.email}",
            metadata_info={
                "requested_amount": float(requested_amount),
                "system_cut": float(system_cut),
                "intasend_fee": float(intasend_fee),
                "payout_amount": float(payout_amount),
                "calculated_at": str(timezone.now())
            }
        )

        # 7. Execute payout
        try:
            payout_response = WithdrawalService._send_mpesa_payout(user, payout_amount)
            intasend_tx_id = payout_response["transactions"][0]["transaction_id"]

            # Update transaction identifier to match IntaSend's transaction_id
            tx.transaction_identifier = intasend_tx_id
            tx.metadata_info.update({
                "payout_response": payout_response,
                "intasend_total_deduction": float(payout_amount + intasend_fee),
                "total_system_wallet_credit": float(system_cut + intasend_fee)
            })
            tx.save(update_fields=["transaction_identifier", "metadata_info"])

        except Exception as e:
            # Rollback balances
            wallet.balance += amount_money
            wallet.save(update_fields=["balance"])

            system_wallet.balance -= Money(system_cut + intasend_fee, "KES")
            system_wallet.save(update_fields=["balance"])

            tx.status = "failed"
            tx.metadata_info.update({"error": str(e)})
            tx.save(update_fields=["status", "metadata_info"])
            logger.error(f"Withdrawal failed for {user.email}: {e}")
            raise e

        return tx

    @staticmethod
    def _send_mpesa_payout(user, payout_amount: Decimal):
        """
        Send actual M-Pesa payout via IntaSend.
        """
        mpesa_number = "254745897362"  # Replace with user.phone or safe retrieval

        service = APIService(
            token=settings.INTASEND_SECRET_KEY.strip(),
            publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
            test=True,
        )

        transactions = [{
            "name": user.username,
            "account": mpesa_number,
            "amount": float(payout_amount)
        }]

        logger.info(f"Sending payout {payout_amount} KES to {mpesa_number}")

        return service.transfer.mpesa(
            currency="KES",
            transactions=transactions,
            requires_approval="NO"
        )


# =======================
# API View
# =======================
class WithdrawAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        requested_amount = Decimal(request.data.get("amount", 0))

        try:
            tx = WithdrawalService.process_withdrawal(request.user, requested_amount)

            response_data = {
                "success": True,
                "message": "Withdrawal initiated successfully",
                "transaction_id": str(tx.id),
                "withdrawal_id": tx.transaction_identifier,
                "status": tx.status,
                "requested_amount": float(tx.metadata_info["requested_amount"]),
                "system_cut": float(tx.metadata_info["system_cut"]),
                "intasend_fee": float(tx.metadata_info["intasend_fee"]),
                "payout_amount": float(tx.metadata_info["payout_amount"]),
                "total_system_wallet_credit": float(tx.metadata_info["total_system_wallet_credit"]),
                "intasend_total_deduction": float(tx.metadata_info["intasend_total_deduction"]),
                "payout_response": tx.metadata_info.get("payout_response", {}),
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Withdrawal failed for {request.user.email}: {e}")
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
