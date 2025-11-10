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
        elif amount < 1000:
            fee = Decimal('5.00')
        else:
            fee = Decimal('7.00')
        
        checkout_amount = amount + fee
        return checkout_amount, fee

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

            # ✅ Calculate checkout amount with fees
            checkout_amount, fee_amount = self._calculate_checkout_amount(amount)
            
            logger.info(f"Original amount: {amount}, Fee: {fee_amount}, Checkout amount: {checkout_amount}")

            client = APIService(
                token=settings.INTASEND_SECRET_KEY.strip(),
                publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
                test=True
            )

            # Build absolute URLs for webhook and redirect
            webhook_url = 'https://ee08464a75c1.ngrok-free.app/api/webhooks/intasend/'
            redirect_url = 'https://ee08464a75c1.ngrok-free.app/api/deposit/success/'

            checkout_data = {
                "amount": float(checkout_amount),  # Use checkout amount with fees
                "currency": "KES",
                "email": user.email,
                "first_name": user.first_name or "User",
                "last_name": user.last_name or "",
                "hosted": True,
                "redirect_url": redirect_url,
                "callback_url": webhook_url,
            }

            logger.info(f"Creating checkout for amount: {checkout_amount} (Original: {amount} + Fee: {fee_amount})")

            response = client.collect.checkout(**checkout_data)
            
            # ✅ Record transaction with fee information
            transaction = Transaction.objects.create(
                wallet=wallet,
                transaction_identifier=response.get("id"),
                amount=amount,  # Store original amount (what user will get)
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
                    "user_pays": float(checkout_amount),  # What user actually pays
                    "user_gets": float(amount),  # What user actually receives
                },
            )

            return Response({
                "message": "Deposit initiated successfully.",
                "checkout_url": response.get("url"),
                "invoice_id": response.get("id"),
                "transaction_id": str(transaction.id),
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

# views.py
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.http import require_http_methods
from apps.transactions.models import Transaction, Wallet
from django.db import transaction
import json
from django.utils import timezone

logger = logging.getLogger(__name__)
@method_decorator(csrf_exempt, name='dispatch')
class IntaSendWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        try:
            # Log raw body for debugging
            raw_body = request.body.decode("utf-8")
            logger.info("🔥 RAW WEBHOOK BODY 🔥")
            logger.info(raw_body)
            try:
                data = json.loads(raw_body)
                challenge = data.get("challenge")
                if challenge and challenge != getattr(settings, "INTASEND_WEBHOOK_CHALLENGE", None):
                    return Response({"error": "Challenge mismatch"}, status=401)
            except Exception as e:
                logger.error(f"Webhook parse error: {e}")

            return Response({"message": "Webhook received"}, status=200)
            # Parse JSON safely
            try:
                data = request.data if request.data else json.loads(raw_body)
            except Exception as e:
                logger.error(f"❌ Failed to parse webhook JSON: {e}")
                return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
            logger.info("📦 FULL WEBHOOK PAYLOAD BELOW ↓↓↓")
            logger.info(json.dumps(data, indent=2))
            logger.info(f"✅ Parsed IntaSend webhook data: {json.dumps(data, indent=2)}")

            # 🔐 Validate webhook challenge
            challenge = data.get("challenge")
            expected_challenge = getattr(settings, "INTASEND_WEBHOOK_CHALLENGE", None)

            if expected_challenge and challenge != expected_challenge:
                logger.warning(f"⚠️ Invalid webhook challenge received: {challenge}")
                return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            # 🧾 Extract key fields
            # IntaSend webhook/response uses 'id' as the main transaction identifier
            intasend_id = data.get("id") or data.get("reference") or data.get("invoice_id")
            state = data.get("state") or data.get("status")
            net_amount = data.get("net_amount") or data.get("amount")

            if not intasend_id:
                logger.warning("⚠️ Webhook missing 'id' field")
                return Response({"warning": "Missing IntaSend transaction id"}, status=status.HTTP_200_OK)

            # 🔎 Match transaction by IntaSend ID
            transaction = Transaction.objects.filter(transaction_identifier=intasend_id).first()
            if not transaction:
                logger.error(f"❌ No transaction found for IntaSend id={intasend_id}")
                return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

            wallet = transaction.wallet

            # 🧠 Store webhook metadata
            metadata = transaction.metadata_info or {}
            metadata["last_webhook"] = data
            transaction.metadata_info = metadata

            # 💰 Handle transaction states
            if state and state.upper() == "COMPLETE":
                transaction.status = "success"
                wallet.balance += transaction.amount
                wallet.save()
                transaction.save()
                logger.info(f"✅ Payment COMPLETE: +{transaction.amount} to wallet {wallet.id}")
                return Response({"status": "success", "intasend_id": intasend_id}, status=status.HTTP_200_OK)

            elif state and state.upper() == "FAILED":
                transaction.status = "failed"
                transaction.save()
                logger.warning(f"❌ Payment FAILED for IntaSend id={intasend_id}")
                return Response({"status": "failed", "intasend_id": intasend_id}, status=status.HTTP_200_OK)

            else:
                transaction.status = "pending"
                transaction.save()
                logger.info(f"⏳ Payment PENDING or UNKNOWN for IntaSend id={intasend_id}")
                return Response({"status": "pending", "intasend_id": intasend_id}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"🔥 Error processing IntaSend webhook: {e}", exc_info=True)
            
    @transaction.atomic
    def _handle_processing_payment(self, transaction_obj, webhook_data):
        """Handle PROCESSING payment - Customer is making payment"""
        try:
            logger.info(f"Processing payment in PROCESSING state for transaction: {transaction_obj.id}")
            
            # Update transaction metadata but don't change status from pending
            current_metadata = transaction_obj.metadata_info or {}
            transaction_obj.metadata_info = {
                **current_metadata,
                "webhook_data": webhook_data,
                "processing_at": str(timezone.now()),
                "provider": webhook_data.get('provider')
            }
            transaction_obj.save()
            
            logger.info(f"Transaction {transaction_obj.id} marked as processing")
            
            return Response({
                "status": "processing",
                "transaction_id": str(transaction_obj.id),
                "message": "Payment is being processed"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            raise
    
    @transaction.atomic
    def _handle_pending_payment(self, transaction_obj, webhook_data):
        """Handle PENDING payment - Transaction just logged"""
        try:
            logger.info(f"Processing payment in PENDING state for transaction: {transaction_obj.id}")
            
            # Update transaction metadata
            current_metadata = transaction_obj.metadata_info or {}
            transaction_obj.metadata_info = {
                **current_metadata,
                "webhook_data": webhook_data,
                "pending_at": str(timezone.now())
            }
            transaction_obj.save()
            
            logger.info(f"Transaction {transaction_obj.id} marked as pending")
            
            return Response({
                "status": "pending",
                "transaction_id": str(transaction_obj.id),
                "message": "Payment is pending"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing pending payment: {str(e)}")
            raise
    
    @transaction.atomic
    def _handle_failed_payment(self, transaction_obj, webhook_data):
        """Handle FAILED payment - Transaction failed"""
        try:
            logger.info(f"Processing FAILED payment for transaction: {transaction_obj.id}")
            
            # Update transaction status
            transaction_obj.status = "failed"
            
            # Update metadata with failure reason
            current_metadata = transaction_obj.metadata_info or {}
            transaction_obj.metadata_info = {
                **current_metadata,
                "webhook_data": webhook_data,
                "failed_at": str(timezone.now()),
                "failed_reason": webhook_data.get('failed_reason'),
                "failed_code": webhook_data.get('failed_code'),
                "webhook_processed": True
            }
            transaction_obj.save()
            
            logger.info(f"Transaction {transaction_obj.id} status updated to: failed")
            logger.info(f"Failure reason: {webhook_data.get('failed_reason')}")
            
            return Response({
                "status": "failed_processed",
                "transaction_id": str(transaction_obj.id),
                "failed_reason": webhook_data.get('failed_reason'),
                "message": "Payment failed and transaction updated"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing failed payment: {str(e)}")
            raise

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
    