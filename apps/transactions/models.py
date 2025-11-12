from django.db import models
from django.core.exceptions import ValidationError
from djmoney.models.fields import MoneyField
from djmoney.money import Money
import uuid

from apps.core.models import Core, User




class Wallet(Core):
    """Represents a user's wallet with balance and account type."""
    ACCOUNT_TYPE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("system", "System"),
    ]

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wallet",
        null=True,
        blank=True
    )

    balance = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='KES',
        default=0.00
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "wallets"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["account_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        owner = self.user.email if self.user else "SYSTEM"
        return f"{owner} - {self.account_type} ({self.balance})"

    def clean(self):
        """Validation logic to enforce wallet rules"""
        if self.account_type == "system":
            existing = Wallet.objects.filter(account_type="system").exclude(id=self.id).exists()
            if existing:
                raise ValidationError("Only one system wallet is allowed.")
            if self.user is not None:
                raise ValidationError("System wallet cannot be linked to a user.")
        else:
            if self.user is None:
                raise ValidationError(f"{self.account_type.capitalize()} wallet must be linked to a user.")

    def save(self, *args, **kwargs):
        self.clean()  
        super().save(*args, **kwargs)

    def can_make_transaction(self, amount):
        if isinstance(amount, Money):
            return self.balance >= amount
        return self.balance >= Money(amount, self.balance.currency)

    def deposit(self, amount, currency='KES'):
        deposit_amount = amount if isinstance(amount, Money) else Money(amount, currency)
        if deposit_amount.currency != self.balance.currency:
            raise ValueError("Currency mismatch in deposit.")
        self.balance += deposit_amount
        self.save(update_fields=["balance"])
        return self.balance

    def withdraw(self, amount, currency='KES'):
        withdraw_amount = amount if isinstance(amount, Money) else Money(amount, currency)
        if withdraw_amount.currency != self.balance.currency:
            raise ValueError("Currency mismatch in withdrawal.")
        if not self.can_make_transaction(withdraw_amount):
            raise ValueError("Insufficient balance")
        self.balance -= withdraw_amount
        self.save(update_fields=["balance"])
        return self.balance

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
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_identifier = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='KES'
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

    related_transaction = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_transactions"
    )

    class Meta:
        db_table = "transactions"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["transaction_identifier"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["wallet", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.transaction_identifier} \
        - {self.transaction_type} ({self.status}) - {self.amount}"

    def is_successful(self):
        return self.status == "success"

    def mark_as_successful(self):
        self.status = "success"
        self.save()

    def mark_as_failed(self, description=None):
        self.status = "failed"
        if description:
            self.description = description
        self.save()

    def get_amount_display(self):
        """Get formatted amount with currency"""
        return f"{self.amount.amount} {self.amount.currency}"


class PaymentWebhookLog(Core):
    """Stores logs for payment webhooks from external payment gateways."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="webhook_logs",
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

    response_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Response sent back to webhook caller"
    )

    class Meta:
        db_table = "payment_webhook_logs"
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["webhook_ref"]),
            models.Index(fields=["processed"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["received_at"]),
        ]

    def __str__(self):
        return f"Webhook {self.webhook_ref or self.id} - {self.event_type or 'Unknown'}"

    def mark_as_processed(self, response_data=None):
        self.processed = True
        if response_data:
            self.response_data = response_data
        self.save()