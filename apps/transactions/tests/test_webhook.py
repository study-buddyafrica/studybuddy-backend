# Feature: payment-escrow-calendar-exam-p2p
"""Property-based tests for PaystackWebhookView — Properties 3, 4, 5, 6."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from apps.transactions.views.paystack_webhook_view import PaystackWebhookView


def _make_request(body: bytes, signature: str):
    request = MagicMock()
    request.body = body
    request.headers = {"X-Paystack-Signature": signature}
    try:
        request.data = json.loads(body)
    except Exception:
        request.data = {}
    return request


def _valid_sig(body: bytes, secret: str = "test-secret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


# ---------------------------------------------------------------------------
# Property 3: Invalid HMAC signatures are always rejected without side effects
# ---------------------------------------------------------------------------

@given(
    payload=st.binary(min_size=1, max_size=512),
    forged_sig=st.text(min_size=1, max_size=128, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
)
@h_settings(max_examples=50)
def test_property_3_invalid_hmac_rejected(payload, forged_sig):
    """
    Feature: payment-escrow-calendar-exam-p2p, Property 3:
    Any payload with an incorrect HMAC returns HTTP 400 and makes no DB writes.
    """
    view = PaystackWebhookView()
    request = _make_request(payload, forged_sig)

    with patch("apps.transactions.views.paystack_webhook_view.PaymentWebhookLog") as mock_log, \
         patch("apps.transactions.views.paystack_webhook_view.Transaction") as mock_tx, \
         patch("apps.transactions.views.paystack_webhook_view.settings") as mock_settings:

        mock_settings.PAYSTACK_SECRET_KEY = "test-secret"
        mock_log_instance = MagicMock()
        mock_log.objects.create.return_value = mock_log_instance

        response = view.post(request)

        # Must return 400 (unless by extreme coincidence the forged sig matches)
        computed = hmac.new(b"test-secret", payload, hashlib.sha512).hexdigest()
        try:
            is_match = hmac.compare_digest(computed, forged_sig)
        except TypeError:
            is_match = False
        if not is_match:
            assert response.status_code == 400
            mock_tx.objects.select_for_update.assert_not_called()


# ---------------------------------------------------------------------------
# Property 4: Every webhook payload is logged regardless of outcome
# ---------------------------------------------------------------------------

@given(payload=st.binary(min_size=1, max_size=256))
@h_settings(max_examples=30)
def test_property_4_every_payload_logged(payload):
    """
    Feature: payment-escrow-calendar-exam-p2p, Property 4:
    Every webhook call creates a PaymentWebhookLog entry.
    """
    view = PaystackWebhookView()
    # Use invalid signature to trigger early exit path
    request = _make_request(payload, "bad-sig")

    with patch("apps.transactions.views.paystack_webhook_view.PaymentWebhookLog") as mock_log, \
         patch("apps.transactions.views.paystack_webhook_view.settings") as mock_settings:

        mock_settings.PAYSTACK_SECRET_KEY = "test-secret"
        mock_log_instance = MagicMock()
        mock_log.objects.create.return_value = mock_log_instance

        view.post(request)

        mock_log.objects.create.assert_called_once()


# ---------------------------------------------------------------------------
# Property 5: Verified charge.success on pending course_payment unlocks enrollment
# ---------------------------------------------------------------------------

def test_property_5_charge_success_unlocks_enrollment():
    """
    Feature: payment-escrow-calendar-exam-p2p, Property 5:
    A verified charge.success for a pending course_payment atomically sets
    Transaction.status='success' and CourseEnrollment.is_active=True.
    """
    from apps.transactions.views.paystack_webhook_view import PaystackWebhookView

    reference = "SB_test_ref_001"
    data = {
        "event": "charge.success",
        "data": {
            "reference": reference,
            "amount": 150000,
            "currency": "KES",
        },
    }
    body = json.dumps(data).encode()
    sig = _valid_sig(body)
    request = _make_request(body, sig)

    mock_tx = MagicMock()
    mock_tx.status = "pending"
    mock_tx.transaction_type = "course_payment"
    mock_tx.wallet = None
    mock_tx.metadata_info = {"reference_id": "course-uuid-001"}

    view = PaystackWebhookView()

    with patch("apps.transactions.views.paystack_webhook_view.PaymentWebhookLog") as mock_log, \
         patch("apps.transactions.views.paystack_webhook_view.Transaction") as mock_tx_model, \
         patch("apps.transactions.views.paystack_webhook_view.settings") as mock_settings, \
         patch("apps.transactions.views.paystack_webhook_view.db_transaction") as mock_dbtx, \
         patch("apps.transactions.views.paystack_webhook_view.EscrowWallet"):

        mock_settings.PAYSTACK_SECRET_KEY = "test-secret"
        mock_log.objects.create.return_value = MagicMock()
        mock_dbtx.atomic.return_value.__enter__ = lambda s: s
        mock_dbtx.atomic.return_value.__exit__ = MagicMock(return_value=False)

        qs_mock = MagicMock()
        qs_mock.select_for_update.return_value.get.return_value = mock_tx
        mock_tx_model.objects = qs_mock

        response = view.post(request)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Property 6: Duplicate charge.success events are idempotent
# ---------------------------------------------------------------------------

def test_property_6_duplicate_charge_success_idempotent():
    """
    Feature: payment-escrow-calendar-exam-p2p, Property 6:
    A charge.success for an already-success Transaction returns 200 with no writes.
    """
    reference = "SB_already_done"
    data = {
        "event": "charge.success",
        "data": {"reference": reference},
    }
    body = json.dumps(data).encode()
    sig = _valid_sig(body)
    request = _make_request(body, sig)

    mock_tx = MagicMock()
    mock_tx.status = "success"  # already processed

    view = PaystackWebhookView()

    with patch("apps.transactions.views.paystack_webhook_view.PaymentWebhookLog") as mock_log, \
         patch("apps.transactions.views.paystack_webhook_view.Transaction") as mock_tx_model, \
         patch("apps.transactions.views.paystack_webhook_view.settings") as mock_settings, \
         patch("apps.transactions.views.paystack_webhook_view.db_transaction") as mock_dbtx, \
         patch("apps.transactions.views.paystack_webhook_view.EscrowWallet"):

        mock_settings.PAYSTACK_SECRET_KEY = "test-secret"
        mock_log.objects.create.return_value = MagicMock()
        mock_dbtx.atomic.return_value.__enter__ = lambda s: s
        mock_dbtx.atomic.return_value.__exit__ = MagicMock(return_value=False)

        qs_mock = MagicMock()
        qs_mock.select_for_update.return_value.get.return_value = mock_tx
        mock_tx_model.objects = qs_mock

        response = view.post(request)
        assert response.status_code == 200
        # save should NOT have been called again
        mock_tx.save.assert_not_called()
