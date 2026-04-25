import uuid
from decimal import Decimal
from django.db import transaction
from djmoney.money import Money
from .models import Wallet, Transaction

@transaction.atomic
def process_session_payment(payment_amount, student_wallet, teacher_wallet):
    """
    Executes a 70/30 split between a teacher and the platform using djmoney.
    Logs all movements in the Transaction table.
    """
    if not isinstance(payment_amount, Money):
        payment_amount = Money(payment_amount, 'KES')

    system_wallet = Wallet.objects.get(account_type='system')

    # FIX: Round the calculated share to exactly 2 decimal places
    teacher_share = round(payment_amount * Decimal('0.70'), 2)
    platform_share = payment_amount - teacher_share 

    # Execute Wallet Updates
    student_wallet.withdraw(payment_amount)
    teacher_wallet.deposit(teacher_share)
    system_wallet.deposit(platform_share)

    # Create the Audit Trail
    base_tx_id = f"SPLIT-{uuid.uuid4().hex[:10].upper()}"

    student_tx = Transaction.objects.create(
        wallet=student_wallet,
        transaction_identifier=f"{base_tx_id}-STUDENT",
        amount=payment_amount,
        transaction_type='payment',
        payment_method='wallet',
        status='success',
        description="Payment for session."
    )

    teacher_tx = Transaction.objects.create(
        wallet=teacher_wallet,
        transaction_identifier=f"{base_tx_id}-TEACHER",
        amount=teacher_share,
        transaction_type='transfer',
        payment_method='wallet',
        status='success',
        description="Session earnings (70%).",
        related_transaction=student_tx 
    )

    Transaction.objects.create(
        wallet=system_wallet,
        transaction_identifier=f"{base_tx_id}-SYS",
        amount=platform_share,
        transaction_type='transfer',
        payment_method='wallet',
        status='success',
        description="Platform commission (30%).",
        related_transaction=student_tx
    )

    return True