"""Transactions signals — triggers escrow release on session completion."""
from django.db.models.signals import post_save
from django.dispatch import receiver


def _connect_signals():
    from apps.school.models import SessionBooking
    from apps.transactions.services.transfer_service import TransferService

    @receiver(
        post_save,
        sender=SessionBooking,
        dispatch_uid="transactions_session_booking_completed",
    )
    def on_session_booking_save(sender, instance, **kwargs):
        if instance.status != "completed":
            return
        # Guard: only release if escrow is still held
        from apps.transactions.models import EscrowWallet
        if not EscrowWallet.objects.filter(
            session_booking=instance, state="held"
        ).exists():
            return
        TransferService().release_escrow(instance)


_connect_signals()
