"""Service for processing session payments with wallet splits."""
from __future__ import annotations

from django.db import transaction
from djmoney.money import Money

from apps.transactions.models import Wallet, Transaction


def process_session_payment(
    payment_amount: Money,
    student_wallet: Wallet,
    teacher_wallet: Wallet,
) -> dict:
    """
    Process a session payment with 70/30 wallet split.

    70% goes to teacher wallet
    30% platform fee (retained or routed to system)

    Args:
        payment_amount: Total amount paid by student
        student_wallet: Student's wallet (for deduction)
        teacher_wallet: Teacher's wallet (for credit)

    Returns:
        dict with transaction details

    Raises:
        ValueError: If insufficient balance
    """
    with transaction.atomic():
        # Deduct full amount from student
        if student_wallet.balance < payment_amount:
            raise ValueError("Insufficient balance in student wallet")

        student_wallet.balance -= payment_amount
        student_wallet.save(update_fields=["balance"])

        # Calculate split: 70% to teacher, 30% platform fee
        teacher_amount = payment_amount * 0.70
        platform_amount = payment_amount * 0.30

        # Credit teacher
        teacher_wallet.balance += teacher_amount
        teacher_wallet.save(update_fields=["balance"])

        # Record transactions
        student_txn = Transaction.objects.create(
            wallet=student_wallet,
            transaction_type="payment",
            amount=payment_amount,
            status="success",
            description="Session payment",
        )

        teacher_txn = Transaction.objects.create(
            wallet=teacher_wallet,
            transaction_type="deposit",
            amount=teacher_amount,
            status="success",
            description="Session payment - teacher share (70%)",
        )

        # Platform fee transaction (system wallet or record)
        # This could go to a system wallet if one exists

    return {
        "student_transaction_id": student_txn.id,
        "teacher_transaction_id": teacher_txn.id,
        "teacher_amount": teacher_amount,
        "platform_fee": platform_amount,
    }
