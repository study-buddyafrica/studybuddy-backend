# Feature: payment-escrow-calendar-exam-p2p
"""Property-based tests for PaymentService."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from apps.transactions.services.payment_service import PaymentService, PaystackAPIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email="student@test.com"):
    user = MagicMock()
    user.email = email
    user.id = "00000000-0000-0000-0000-000000000001"
    user.wallet = None
    return user


PAYSTACK_OK_RESPONSE = {
    "status": True,
    "message": "Authorization URL created",
    "data": {
        "authorization_url": "https://checkout.paystack.com/abc123",
        "access_code": "abc123",
        "reference": "SB_ref",
    },
}


# ---------------------------------------------------------------------------
# Property 1: Payment initiation creates a correct pending transaction
# ---------------------------------------------------------------------------

@given(amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000"), allow_nan=False, allow_infinity=False))
@h_settings(max_examples=50)
def test_property_1_initiation_creates_pending_transaction(amount):
    """
    Feature: payment-escrow-calendar-exam-p2p, Property 1:
    For any valid positive amount, initiate_checkout creates a Transaction
    with status='pending' and payment_method='paystack'.
    """
    user = _make_user()
    service = PaymentService()

    with patch("apps.transactions.services.payment_service.requests.post") as mock_post, \
         patch.object(PaymentService, "_create_pending_transaction") as mock_create:

        mock_response = MagicMock()
        mock_response.json.return_value = PAYSTACK_OK_RESPONSE
        mock_post.return_value = mock_response

        fake_tx = MagicMock()
        fake_tx.id = "tx-uuid"
        mock_create.return_value = fake_tx

        result = service.initiate_checkout(
            user=user,
            amount=amount,
            currency="KES",
            transaction_type="course_payment",
            reference_id="ref-001",
        )

        assert result["checkout_url"] == PAYSTACK_OK_RESPONSE["data"]["authorization_url"]
        assert result["transaction_id"] == "tx-uuid"
        assert result["reference"].startswith("SB_")

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["payment_method"] == "paystack"
        assert call_kwargs["transaction_type"] == "course_payment"


# ---------------------------------------------------------------------------
# Property 2: Non-positive amounts are always rejected
# ---------------------------------------------------------------------------

@given(amount=st.one_of(
    st.decimals(max_value=Decimal("0"), allow_nan=False, allow_infinity=False),
    st.just(0),
    st.just(-1),
))
@h_settings(max_examples=50)
def test_property_2_non_positive_amounts_rejected(amount):
    """
    Feature: payment-escrow-calendar-exam-p2p, Property 2:
    For any amount <= 0, initiate_checkout raises ValidationError and
    creates no Transaction record.
    """
    from rest_framework.exceptions import ValidationError

    user = _make_user()
    service = PaymentService()

    with patch("apps.transactions.services.payment_service.requests.post") as mock_post, \
         patch.object(PaymentService, "_create_pending_transaction") as mock_create:

        with pytest.raises(ValidationError):
            service.initiate_checkout(
                user=user,
                amount=amount,
                currency="KES",
                transaction_type="course_payment",
                reference_id="ref-001",
            )

        mock_post.assert_not_called()
        mock_create.assert_not_called()
