from rest_framework.routers import DefaultRouter
from django.urls import path

from apps.transactions.views.withdrawal_confirmation import IntaSendWebhookView
from apps.transactions.views.paystack_webhook_view import PaystackWebhookView
from apps.transactions.views.paystack_payment_view import PaystackPaymentView
from apps.transactions.views.payment_success_view import deposit_success_view
from apps.transactions.views.deposit_view import DepositAPIView
from apps.transactions.views.wallet_view import WalletViewSet
from apps.transactions.views.transactions_view import TransactionViewSet
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
    path(
        "wallet/deposit/", 
        DepositAPIView.as_view(), 
        name="wallet-deposit"
    ),
    path(
        'transactions/webhook', 
        PaystackWebhookView.as_view(), 
        name='paystack-webhook'
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
    path(
        'withdraw/', 
        WithdrawAPIView.as_view(), 
        name='withdraw'
    ),
    
]+transaction_router.urls