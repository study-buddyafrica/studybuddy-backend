"""Tests for TransferService — 70/30 escrow settlement calculation and payout releases."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.conf import settings
from djmoney.money import Money

from apps.transactions.models import EscrowWallet
from apps.transactions.services.transfer_service import (
    TransferService,
    PAYSTACK_TRANSFER_URL,
)


# ---------------------------------------------------------------------------
# 1. Escrow Split Calculation Tests (70/30 Split - SAD §1.2.1 / §8.2)
# ---------------------------------------------------------------------------


def test_calculate_payout_default_70_30_split():
    """
    SAD §8.2: With default 30% platform fee, teacher receives 70%.
    Gross KES 1,000 -> Teacher KES 700.00
    """
    gross = Money(Decimal("1000.00"), "KES")
    payout = TransferService._calculate_payout(gross)
    assert payout.amount == Decimal("700.00")
    assert str(payout.currency) == "KES"


def test_calculate_payout_sad_example_amount():
    """
    SAD §8.2 Worked Example:
    Gross Amount: KES 1,250.00
    Teacher Share (70%): round(1250 * 0.70, 2) = KES 875.00
    Platform Commission (30%): KES 375.00
    """
    gross = Money(Decimal("1250.00"), "KES")
    payout = TransferService._calculate_payout(gross)
    assert payout.amount == Decimal("875.00")


def test_calculate_payout_custom_override(settings):
    """
    Overriding PLATFORM_FEE_PERCENT alters the payout multiplier.
    """
    settings.PLATFORM_FEE_PERCENT = 20.0
    gross = Money(Decimal("1000.00"), "KES")
    payout = TransferService._calculate_payout(gross)
    assert payout.amount == Decimal("800.00")


# ---------------------------------------------------------------------------
# 2. Release Escrow Lifecycle & Failure Handling
# ---------------------------------------------------------------------------


def test_release_escrow_no_held_escrow():
    """
    If no 'held' EscrowWallet exists for the booking, release_escrow returns cleanly.
    """
    booking = MagicMock()
    booking.id = "booking-123"

    with patch.object(EscrowWallet.objects, "select_for_update") as mock_sfu:
        mock_qs = MagicMock()
        mock_qs.get.side_effect = EscrowWallet.DoesNotExist
        mock_sfu.return_value = mock_qs

        service = TransferService()
        # Should not raise
        service.release_escrow(booking)


def test_release_escrow_missing_teacher_recipient_code():
    """
    If teacher has no paystack_recipient_code, escrow state transitions to 'failed'.
    """
    booking = MagicMock()
    booking.id = "booking-123"
    booking.teacher = MagicMock()
    booking.teacher.id = "teacher-123"
    booking.teacher.paystack_recipient_code = None

    mock_escrow = MagicMock()
    mock_escrow.state = "held"

    with patch.object(EscrowWallet.objects, "select_for_update") as mock_sfu, \
         patch("apps.transactions.services.transfer_service.db_transaction.atomic"):
        mock_qs = MagicMock()
        mock_qs.get.return_value = mock_escrow
        mock_sfu.return_value = mock_qs

        service = TransferService()
        service.release_escrow(booking)

        assert mock_escrow.state == "failed"
        mock_escrow.save.assert_called_once_with(update_fields=["state"])


def test_release_escrow_paystack_network_error():
    """
    If requests.post raises RequestException, escrow transitions to 'failed'.
    """
    booking = MagicMock()
    booking.id = "booking-123"
    booking.teacher = MagicMock()
    booking.teacher.paystack_recipient_code = "RCP_teacher_123"

    mock_escrow = MagicMock()
    mock_escrow.state = "held"
    mock_escrow.amount = Money(Decimal("1000.00"), "KES")

    with patch.object(EscrowWallet.objects, "select_for_update") as mock_sfu, \
         patch("apps.transactions.services.transfer_service.requests.post") as mock_post, \
         patch("apps.transactions.services.transfer_service.db_transaction.atomic"):
        mock_qs = MagicMock()
        mock_qs.get.return_value = mock_escrow
        mock_sfu.return_value = mock_qs

        mock_post.side_effect = requests.RequestException("Connection timeout")

        service = TransferService()
        service.release_escrow(booking)

        assert mock_escrow.state == "failed"
        mock_escrow.save.assert_called_once_with(update_fields=["state"])


def test_release_escrow_paystack_api_rejection():
    """
    If Paystack returns status: False, escrow transitions to 'failed'.
    """
    booking = MagicMock()
    booking.id = "booking-123"
    booking.teacher = MagicMock()
    booking.teacher.paystack_recipient_code = "RCP_teacher_123"

    mock_escrow = MagicMock()
    mock_escrow.state = "held"
    mock_escrow.amount = Money(Decimal("1000.00"), "KES")

    with patch.object(EscrowWallet.objects, "select_for_update") as mock_sfu, \
         patch("apps.transactions.services.transfer_service.requests.post") as mock_post, \
         patch("apps.transactions.services.transfer_service.db_transaction.atomic"):
        mock_qs = MagicMock()
        mock_qs.get.return_value = mock_escrow
        mock_sfu.return_value = mock_qs

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": False, "message": "Insufficient balance"}
        mock_post.return_value = mock_resp

        service = TransferService()
        service.release_escrow(booking)

        assert mock_escrow.state == "failed"
        mock_escrow.save.assert_called_once_with(update_fields=["state"])


def test_release_escrow_success_creates_transaction_and_releases():
    """
    On Paystack success:
    1. Transfer payload dispatched with calculated 70% payout in minor subunits.
    2. Transaction created with transaction_type='escrow_release'.
    3. Escrow state transitions to 'released'.
    """
    booking = MagicMock()
    booking.id = "booking-123"
    booking.teacher = MagicMock()
    booking.teacher.paystack_recipient_code = "RCP_teacher_123"

    mock_escrow = MagicMock()
    mock_escrow.state = "held"
    mock_escrow.amount = Money(Decimal("1000.00"), "KES")
    mock_escrow.held_transaction = MagicMock()

    with patch.object(EscrowWallet.objects, "select_for_update") as mock_sfu, \
         patch("apps.transactions.services.transfer_service.requests.post") as mock_post, \
         patch("apps.transactions.services.transfer_service.Transaction") as mock_tx_cls, \
         patch("apps.transactions.services.transfer_service.db_transaction.atomic"):
        mock_qs = MagicMock()
        mock_qs.get.return_value = mock_escrow
        mock_sfu.return_value = mock_qs

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": True,
            "message": "Transfer queued",
            "data": {"transfer_code": "TRF_998877"},
        }
        mock_post.return_value = mock_resp

        mock_release_tx = MagicMock()
        mock_tx_cls.objects.create.return_value = mock_release_tx

        service = TransferService()
        service.release_escrow(booking)

        # 70% of 1000 KES = 700 KES = 70000 subunits
        assert mock_post.call_count == 1
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["amount"] == 70000
        assert call_kwargs["json"]["recipient"] == "RCP_teacher_123"

        mock_tx_cls.objects.create.assert_called_once()
        create_kwargs = mock_tx_cls.objects.create.call_args[1]
        assert create_kwargs["transaction_type"] == "escrow_release"
        assert create_kwargs["amount"] == Decimal("700.00")

        assert mock_escrow.state == "released"
        assert mock_escrow.release_transaction == mock_release_tx
        mock_escrow.save.assert_called_once_with(
            update_fields=["release_transaction", "state"]
        )
