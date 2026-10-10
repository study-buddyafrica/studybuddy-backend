from rest_framework.routers import DefaultRouter
from django.urls import path

# Active Paystack & Core Transaction Views
from apps.transactions.views.paystack_webhook_view import PaystackWebhookView
from apps.transactions.views.paystack_payment_view import PaystackPaymentView
from apps.transactions.views.payment_success_view import deposit_success_view
from apps.transactions.views.wallet_view import WalletViewSet
from apps.transactions.views.transactions_view import TransactionViewSet
from apps.transactions.views.paystack_withdrawal_view import PaystackWithdrawalView
from apps.users.views.paystack_recipient_view import PaystackRecipientView

# Legacy IntaSend Views (Deprecated & Safely Isolated)
from apps.transactions.views.withdrawal_confirmation import IntaSendWebhookView
from apps.transactions.views.deposit_view import DepositAPIView
from apps.transactions.views.withdrawal_view import WithdrawAPIView

transaction_router = DefaultRouter()
transaction_router.register(
    r'transactions',
    TransactionViewSet
)
transaction_router.register(
    r'wallet',
    WalletViewSet
)

urlpatterns = [
    # Paystack Deposit Initiation (Primary & Backward-Compatible Route)
    path(
        "wallet/deposit/",
        PaystackPaymentView.as_view(),
        name="wallet-deposit"
    ),
    path(
        'transactions/paystack/initiate/',
        PaystackPaymentView.as_view(),
        name='paystack-initiate'
    ),
    path(
        'deposit/success/',
        deposit_success_view,
        name='deposit-success'
    ),

    # Paystack Webhook (Signed HMAC SHA512 + Redis Idempotency)
    path(
        'transactions/webhook',
        PaystackWebhookView.as_view(),
        name='paystack-webhook'
    ),
    path(
        'transactions/webhook/',
        PaystackWebhookView.as_view(),
        name='paystack-webhook-slash'
    ),

    # Teacher Payout & Recipient Routes (Paystack Transfers)
    path(
        'wallet/withdraw/',
        PaystackWithdrawalView.as_view(),
        name='paystack-withdraw'
    ),
    path(
        'withdraw/',
        PaystackWithdrawalView.as_view(),
        name='withdraw'
    ),
    path(
        'wallet/payout-recipient/',
        PaystackRecipientView.as_view(),
        name='payout-recipient'
    ),

    # Legacy IntaSend Endpoints (Deprecated — Isolated for Rollback Safety)
    path(
        'legacy/intasend/deposit/',
        DepositAPIView.as_view(),
        name='legacy-intasend-deposit'
    ),
    path(
        'legacy/intasend/withdraw/',
        WithdrawAPIView.as_view(),
        name='legacy-intasend-withdraw'
    ),
    path(
        'legacy/intasend/webhook/',
        IntaSendWebhookView.as_view(),
        name='legacy-intasend-webhook'
    ),

] + transaction_router.urls
