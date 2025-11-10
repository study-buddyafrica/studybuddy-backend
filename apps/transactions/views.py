import logging
from decimal import Decimal
from rest_framework import viewsets
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from intasend import APIService
from apps.transactions  .models import Wallet, Transaction
from django.urls import reverse
from apps.transactions.serializers import WalletSerializer,TransactionSerializer
import uuid

logger = logging.getLogger(__name__)
class DepositAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _calculate_checkout_amount(self, amount):
        """
        Calculate the total checkout amount including IntaSend fees
        Returns: (checkout_amount, fee_amount)
        """
        amount = Decimal(amount)
        
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        if amount < 100:
            fee = Decimal('2.00')
        elif amount < 500:
            fee = Decimal('4.00')
        else:
            fee = Decimal('5.00')
        
        checkout_amount = amount + fee
        return checkout_amount, fee

    def _get_fee_structure(self):
        """Return the fee structure for transparency"""
        return {
            "fee_structure": [
                {"range": "Below 100 KES", "fee": "2 KES"},
                {"range": "100 KES - 499 KES", "fee": "4 KES"},
                {"range": "500 KES and above", "fee": "5 KES"},
            ],
            "note": "Fees are added to ensure you receive the exact amount deposited"
        }

    def post(self, request):
        try:
            amount = Decimal(request.data.get("amount", 0))
            if amount <= 0:
                return Response(
                    {"error": "Amount must be greater than 0."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user = request.user
            wallet, created = Wallet.objects.get_or_create(user=user)

            # Calculate checkout amount with fees
            checkout_amount, fee_amount = self._calculate_checkout_amount(amount)
            
            logger.info(f"Original amount: {amount}, Fee: {fee_amount}, Checkout amount: {checkout_amount}")

            client = APIService(
                token=settings.INTASEND_SECRET_KEY.strip(),
                publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
                test=True
            )

            # Build absolute URLs for webhook and redirect
            webhook_url = request.build_absolute_uri(reverse('intasend-webhook'))
            redirect_url = request.build_absolute_uri(reverse('deposit-success'))

            # ✅ Generate unique api_ref that we'll use as transaction identifier
            api_ref = f"deposit_{user.id}_{uuid.uuid4().hex[:8]}"

            checkout_data = {
                "amount": float(checkout_amount),
                "currency": "KES",
                "email": user.email,
                "first_name": user.first_name or "User",
                "last_name": user.last_name or "",
                "hosted": True,
                "redirect_url": redirect_url,
                "callback_url": webhook_url,
                "api_ref": api_ref,  # This will be our primary identifier
            }

            logger.info(f"Creating checkout with api_ref: {api_ref}")

            response = client.collect.checkout(**checkout_data)
            
            # ✅ Use api_ref as the transaction identifier
            transaction = Transaction.objects.create(
                wallet=wallet,
                transaction_identifier=api_ref,  # ✅ Use api_ref as primary identifier
                amount=amount,
                transaction_type="deposit",
                payment_method="intasend",
                status="pending",
                description=f"Deposit initiated - {user.email}",
                metadata_info={
                    "checkout_data": checkout_data,
                    "intasend_response": response,
                    "user_id": str(user.id),
                    "webhook_url": webhook_url,
                    "redirect_url": redirect_url,
                    "fee_details": {
                        "original_amount": float(amount),
                        "fee_amount": float(fee_amount),
                        "checkout_amount": float(checkout_amount),
                        "fee_structure": self._get_fee_structure(),
                    },
                    "user_pays": float(checkout_amount),
                    "user_gets": float(amount),
                    # Store other identifiers for reference
                    "other_identifiers": {
                        "intasend_id": response.get("id"),
                        "invoice_id": None,  # Will be populated by webhook
                        "tracking_id": response.get("tracking_id"),
                    }
                },
            )

            logger.info(f"Transaction created with identifier: {api_ref}")

            return Response({
                "message": "Deposit initiated successfully.",
                "checkout_url": response.get("url"),
                "transaction_id": str(transaction.id),
                "api_ref": api_ref,  # Return api_ref to client
                "amount_details": {
                    "original_amount": float(amount),
                    "fee_amount": float(fee_amount),
                    "total_checkout_amount": float(checkout_amount),
                    "you_pay": float(checkout_amount),
                    "you_get": float(amount),
                },
                "fee_breakdown": self._get_fee_structure(),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Deposit initiation failed: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to initiate deposit: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# views.py
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.http import require_http_methods
from apps.transactions.models import Transaction, Wallet
from django.db import transaction as db_transaction
from django.db import transaction
import json
from django.utils import timezone
from djmoney.money import Money
from decimal import Decimal

logger = logging.getLogger(__name__)
@method_decorator(csrf_exempt, name='dispatch')

class IntaSendWebhookView(APIView):
    """
    Handles incoming webhook notifications from IntaSend
    """

    def post(self, request, *args, **kwargs):
        webhook_data = request.data
        state = webhook_data.get("state")
        invoice_id = webhook_data.get("invoice_id")
        api_ref = webhook_data.get("api_ref")

        logger.info(f"🔔 IntaSend webhook received: {invoice_id=} {state=}")

        # Lookup transaction by reference you set during checkout
        transaction_obj = Transaction.objects.filter(
            metadata_info__intasend_response__api_ref=api_ref
        ).first()

        if not transaction_obj:
            logger.warning(f"❌ No transaction found for api_ref={api_ref}")
            return Response({"error": "transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        # Handle each possible state
        if state == "COMPLETE":
            return self._handle_complete_payment(transaction_obj, webhook_data)
        elif state in ["FAILED", "CANCELLED"]:
            return self._handle_failed_payment(transaction_obj, webhook_data)
        elif state in ["PROCESSING", "PENDING"]:
            return self._handle_pending_payment(transaction_obj, webhook_data)
        else:
            logger.warning(f"⚠️ Unknown state received: {state}")
            return Response({"error": "unknown state"}, status=status.HTTP_400_BAD_REQUEST)

    # -----------------------------
    # Internal helpers
    # -----------------------------

    
    def _handle_complete_payment(self, transaction_obj, data):
        """Handle successful payment (credit user with original amount only)"""
        logger.info(f"✅ Completing payment for transaction {transaction_obj.id}")

        with db_transaction.atomic():
            # Update transaction info
            transaction_obj.status = "completed"
            transaction_obj.metadata_info["webhook_update"] = data
            transaction_obj.save()

            # --- Get the original amount user intended to deposit ---
            metadata = transaction_obj.metadata_info or {}
            fee_details = metadata.get("fee_details", {})

            # Extract original amount safely
            original_amount_value = (
                fee_details.get("original_amount") or
                metadata.get("user_gets") or
                transaction_obj.amount
            )

            try:
                original_amount_value = Decimal(original_amount_value)
            except Exception:
                logger.warning("⚠️ Could not parse original_amount, using transaction.amount instead")
                original_amount_value = transaction_obj.amount

            # Use the same currency as transaction
            currency = transaction_obj.amount_currency or "KES"
            credit_amount = Money(original_amount_value, currency)

            # --- Update wallet balance ---
            wallet = transaction_obj.wallet
            wallet.balance += credit_amount
            wallet.save()

            # Store for reference
            transaction_obj.metadata_info["credited_amount"] = float(credit_amount.amount)
            transaction_obj.save()

        logger.info(
            f"💰 Wallet {wallet.id} credited with {credit_amount} (original amount from metadata)"
        )

        return Response(
            {"status": "completed", "credited_amount": float(credit_amount.amount)},
            status=status.HTTP_200_OK,
        )

    def _handle_failed_payment(self, transaction_obj, data):
        """Handle failed or cancelled payments"""
        logger.info(f"❌ Payment failed/cancelled for transaction {transaction_obj.id}")

        transaction_obj.status = "failed"
        transaction_obj.metadata_info["webhook_update"] = data
        transaction_obj.save()

        return Response({"status": "failed"}, status=status.HTTP_200_OK)

    def _handle_pending_payment(self, transaction_obj, data):
        """Handle pending/processing payments"""
        logger.info(f"⌛ Payment still pending for transaction {transaction_obj.id}")

        transaction_obj.status = "processing"
        transaction_obj.metadata_info["webhook_update"] = data
        transaction_obj.save()

        return Response({"status": "processing"}, status=status.HTTP_200_OK)

# views.py
from django.shortcuts import render

def deposit_success_view(request):
    """
    Page users are redirected to after successful payment
    """
    tracking_id = request.GET.get('tracking_id')
    checkout_id = request.GET.get('checkout_id')
    
    context = {
        'tracking_id': tracking_id,
        'checkout_id': checkout_id,
        'message': 'Payment completed successfully! Your wallet will be updated shortly.'
    }
    
    return render(request, 'payments/success.html', context)


class WalletViewSet(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()
    