from django.db.models.signals import post_save
from django.dispatch import receiver
from djmoney.money import Money

from apps.users.models import User
from apps.transactions.models import Wallet 

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if not created:
        return

    if hasattr(instance, "wallet"):
        return

    if instance.is_superuser:
        account_type = "system"
    elif instance.role == "teacher":
        account_type = "teacher"
    elif instance.role == "parent":
        account_type = "parent"
    else:
        account_type = "student"

    Wallet.objects.create(
        user=instance,
        account_type=account_type,
        failed_withdraw_attempts=0,
        balance=Money(0, "KES"),
    )
