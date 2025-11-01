from django.db import models
from apps.core.models import Core
import uuid


class Wallet(Core):
    """Represents a user's wallet with balance and account type."""
    ACCOUNT_TYPE_CHOICES = [
        ("personal", "Personal"),
        ("teacher", "Teacher"),
        ("school", "School"),
        ("admin", "Admin"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        "User",
        on_delete=models.CASCADE,
        related_name="wallet"
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="personal",
    )

    currency = models.CharField(
        max_length=10,
        default="KES",
    )

    class Meta:
        db_table = "wallets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account_type"]),
            models.Index(fields=["currency"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.account_type} ({self.balance} {self.currency})"
    

class Transaction(Core):
    """Represents a financial transaction tied to a user's wallet."""
    TRANSACTION_TYPE_CHOICES = [
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("payment", "Payment"),
        ("refund", "Refund"),
        ("transfer", "Transfer"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("card", "Card"),
        ("bank", "Bank Transfer"),
        ("intasend", "IntaSend"),
        ("paypal", "PayPal"),
        ("wallet", "Wallet"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("reversed", "Reversed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wallet = models.ForeignKey(
        "Wallet",
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_identifier = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="KES",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    account_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    metadata_info = models.JSONField(
        null=True,
        blank=True,
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["transaction_identifier"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.transaction_identifier} - {self.transaction_type} ({self.status})"


class PaymentWebhookLog(Core):
    """Stores logs for payment webhooks from external payment gateways."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.CASCADE,
        related_name="webhooks",
        null=True,
        blank=True,
    )

    webhook_ref = models.CharField(
        max_length=150,
        db_index=True,
        null=True,
        blank=True,
    )

    payload = models.JSONField()

    received_at = models.DateTimeField(auto_now_add=True)

    processed = models.BooleanField(default=False)

    status_code = models.IntegerField(
        null=True,
        blank=True,
    )

    event_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    remarks = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "payment_webhook_logs"
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["webhook_ref"]),
            models.Index(fields=["processed"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"Webhook {self.webhook_ref or self.id} - {self.event_type or 'Unknown'}"