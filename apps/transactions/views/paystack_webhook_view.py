"""PaystackWebhookView — receives and processes Paystack event callbacks."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.db import transaction as db_transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.transactions.models import Transaction, Wallet, PaymentWebhookLog, EscrowWallet

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Receive Paystack webhook events",
        request=dict,
        responses={
            200: OpenApiResponse(description="Webhook accepted"),
            400: OpenApiResponse(description="Invalid signature or payload"),
        },
    )
    def post(self, request):
        payload_bytes = request.body
        signature = request.headers.get("X-Paystack-Signature", "")

        # Always log the raw payload first
        log_entry = PaymentWebhookLog.objects.create(
            payload=request.data if isinstance(request.data, dict) else {},
            event_type=None,
            processed=False,
        )

        if not self._verify_signature(payload_bytes, signature):
            logger.warning("Paystack webhook: invalid HMAC signature")
            log_entry.remarks = "rejected: invalid signature"
            log_entry.status_code = 400
            log_entry.save(update_fields=["remarks", "status_code"])
            return Response({"error": "invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = json.loads(payload_bytes)
        except (json.JSONDecodeError, ValueError):
            log_entry.remarks = "rejected: invalid JSON"
            log_entry.status_code = 400
            log_entry.save(update_fields=["remarks", "status_code"])
            return Response({"error": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        event = data.get("event", "")
        log_entry.event_type = event
        log_entry.payload = data
        log_entry.save(update_fields=["event_type", "payload"])

        try:
            if event == "charge.success":
                self._handle_charge_success(data.get("data", {}))
            elif event == "transfer.success":
                self._handle_transfer_success(data.get("data", {}))
        except Exception as exc:
            logger.exception("Paystack webhook processing error: %s", exc)
            log_entry.remarks = f"error: {exc}"
            log_entry.status_code = 200
            log_entry.save(update_fields=["remarks", "status_code"])
            # Still return 200 to prevent Paystack retries
            return Response({"status": "ok"}, status=status.HTTP_200_OK)

        log_entry.processed = True
        log_entry.status_code = 200
        log_entry.save(update_fields=["processed", "status_code"])
        return Response({"status": "ok"}, status=status.HTTP_200_OK)

    @staticmethod
    def _verify_signature(payload_bytes: bytes, signature: str) -> bool:
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "").encode()
        computed = hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()
        try:
            return hmac.compare_digest(computed, signature)
        except TypeError:
            return False

    @staticmethod
    def _handle_charge_success(data: dict) -> None:
        reference = data.get("reference")
        if not reference:
            return

        with db_transaction.atomic():
            try:
                tx = Transaction.objects.select_for_update().get(
                    transaction_identifier=reference
                )
            except Transaction.DoesNotExist:
                logger.warning("charge.success: no transaction for ref=%s", reference)
                return

            # Idempotency guard
            if tx.status == "success":
                logger.info("charge.success: already processed ref=%s", reference)
                return

            tx.status = "success"
            tx.save(update_fields=["status"])

            # Credit the wallet
            if tx.wallet:
                tx.wallet.deposit(tx.amount)

            # Unlock course enrollment
            if tx.transaction_type == "course_payment":
                from apps.school.models import CourseEnrollment
                metadata = tx.metadata_info or {}
                ref_id = metadata.get("reference_id")
                if ref_id:
                    CourseEnrollment.objects.filter(
                        course_id=ref_id, student__user__wallet=tx.wallet
                    ).update(is_active=True)

            # Create escrow for session payments
            elif tx.transaction_type == "session_payment":
                metadata = tx.metadata_info or {}
                ref_id = metadata.get("reference_id")
                if ref_id:
                    from apps.school.models import SessionBooking
                    try:
                        booking = SessionBooking.objects.get(id=ref_id)
                        EscrowWallet.objects.get_or_create(
                            session_booking=booking,
                            defaults={
                                "amount": tx.amount,
                                "state": "held",
                                "held_transaction": tx,
                            },
                        )
                    except SessionBooking.DoesNotExist:
                        logger.warning("charge.success: no booking for ref_id=%s", ref_id)

    @staticmethod
    def _handle_transfer_success(data: dict) -> None:
        transfer_code = data.get("transfer_code")
        if not transfer_code:
            return

        with db_transaction.atomic():
            tx = Transaction.objects.filter(
                metadata_info__transfer_code=transfer_code
            ).select_for_update().first()
            if not tx:
                logger.warning("transfer.success: no transaction for code=%s", transfer_code)
                return

            tx.status = "success"
            tx.save(update_fields=["status"])

            # Mark escrow as released
            escrow = EscrowWallet.objects.filter(
                release_transaction=tx
            ).select_for_update().first()
            if escrow:
                escrow.state = "released"
                escrow.save(update_fields=["state"])
