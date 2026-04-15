from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.transactions.models import Transaction
from django.db import transaction as db_transaction
from djmoney.money import Money
from decimal import Decimal

@method_decorator(csrf_exempt, name='dispatch')
class IntaSendDepositWebhookView(APIView):
    def _is_valid_webhook(self, request):
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
            return Response({"error": "invalid webhook signature"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        state = data.get("state")
        api_ref = data.get("api_ref")

        tx = Transaction.objects.filter(metadata_info__intasend_response__api_ref=api_ref).first()
        if not tx:
            return Response({"error": "transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        tx.metadata_info["webhook_update"] = data

        state_map = {
            "FAILED": "failed",
            "CANCELLED": "failed",
            "PROCESSING": "processing",
            "PENDING": "processing",
            "COMPLETE": "completed",
        }

        tx.status = state_map.get(state, None)
        if not tx.status:
            return Response({"error": "unknown state"}, status=status.HTTP_400_BAD_REQUEST)

        if tx.status == "completed":
            with db_transaction.atomic():
                metadata = tx.metadata_info or {}
                fee = metadata.get("fee_details", {})
                original = fee.get("original_amount") or metadata.get("user_gets") or tx.amount
                try:
                    original = Decimal(original)
                except Exception:
                    original = tx.amount

                amount = Money(original, tx.amount_currency or "KES")
                tx.wallet.balance += amount
                tx.wallet.save()
                tx.metadata_info["credited_amount"] = float(amount.amount)

        tx.save()
        return Response({"status": tx.status}, status=status.HTTP_200_OK)