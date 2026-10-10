"""PaystackWebhookView — receives and processes Paystack event callbacks."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.core.cache import cache
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

        # Redis idempotency guard for charge.success events
        if event == "charge.success":
            event_id = str(data.get("data", {}).get("id", ""))
            if event_id:
                cache_key = f"paystack:webhook:{event_id}"
                # Returns True if key was newly set (not duplicate), False if already processed
                is_new = cache.set(cache_key, True, timeout=86400, nx=True)
                if not is_new:
                    logger.info("Paystack webhook: duplicate charge.success event_id=%s", event_id)
                    log_entry.remarks = "duplicate event ignored"
                    log_entry.status_code = 200
                    log_entry.save(update_fields=["remarks", "status_code"])
                    return Response({"status": "ok"}, status=status.HTTP_200_OK)

        try:
            if event == "charge.success":
                self._handle_charge_success(data.get("data", {}))
            elif event == "transfer.success":
                self._handle_transfer_success(data.get("data", {}))
            elif event in ("transfer.failed", "transfer.reversed"):
                self._handle_transfer_failed(data.get("data", {}))
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

            # Idempotency guard (database level)
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
        reference = data.get("reference")
        if not transfer_code and not reference:
            return

        with db_transaction.atomic():
            tx = None
            if transfer_code:
                tx = (
                    Transaction.objects.filter(
                        metadata_info__transfer_code=transfer_code
                    )
                    .select_for_update()
                    .first()
                )
            if not tx and reference:
                tx = (
                    Transaction.objects.filter(transaction_identifier=reference)
                    .select_for_update()
                    .first()
                )

            if not tx:
                logger.warning(
                    "transfer.success: no transaction for code=%s reference=%s",
                    transfer_code,
                    reference,
                )
                return

            if tx.status == "success":
                logger.info("transfer.success: tx %s already processed", tx.id)
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

    @staticmethod
    def _handle_transfer_failed(data: dict) -> None:
        transfer_code = data.get("transfer_code")
        reference = data.get("reference")
        reason = (
            data.get("reason")
            or data.get("complete_message")
            or data.get("message")
            or "Transfer failed or reversed by provider"
        )

        if not transfer_code and not reference:
            logger.warning("transfer.failed/reversed: missing both transfer_code and reference")
            return

        with db_transaction.atomic():
            tx = None
            if transfer_code:
                tx = (
                    Transaction.objects.filter(
                        metadata_info__transfer_code=transfer_code
                    )
                    .select_for_update()
                    .first()
                )
            if not tx and reference:
                tx = (
                    Transaction.objects.filter(transaction_identifier=reference)
                    .select_for_update()
                    .first()
                )

            if not tx:
                logger.warning(
                    "transfer.failed/reversed: no transaction for code=%s reference=%s",
                    transfer_code,
                    reference,
                )
                return

            if tx.status == "failed":
                logger.info("transfer.failed/reversed: tx %s already marked failed", tx.id)
                return

            # Update transaction status and metadata
            tx.status = "failed"
            metadata = dict(tx.metadata_info or {})
            metadata["failure_reason"] = reason
            if transfer_code and "transfer_code" not in metadata:
                metadata["transfer_code"] = transfer_code
            tx.metadata_info = metadata
            tx.save(update_fields=["status", "metadata_info"])

            # Atomically refund debited funds back to the user's wallet
            if tx.wallet:
                wallet = Wallet.objects.select_for_update().get(id=tx.wallet_id)
                wallet.deposit(tx.amount)
                logger.info(
                    "Refunded %s to wallet %s for failed transfer tx=%s",
                    tx.amount,
                    wallet.id,
                    tx.id,
                )

            # Update EscrowWallet if this transfer was linked to escrow release
            escrow = (
                EscrowWallet.objects.filter(release_transaction=tx)
                .select_for_update()
                .first()
            )
            if escrow:
                escrow.state = "failed"
                escrow.save(update_fields=["state"])
                logger.warning("Escrow %s marked failed following transfer failure", escrow.id)
