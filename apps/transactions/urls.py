from rest_framework.routers import DefaultRouter
from django.urls import path

from apps.transactions.views.payment_confirmation import IntaSendWebhookView
from apps.transactions.views.payment_success_view import deposit_success_view
from apps.transactions.views.deposit_view import DepositAPIView
from apps.transactions.views.wallet_view import WalletViewSet
from apps.transactions.views.transactions_view import TransactionViewSet

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
        'webhooks/intasend/', 
        IntaSendWebhookView.as_view(), 
        name='intasend-webhook'
        ),
    path(
        'deposit/success/', 
        deposit_success_view, 
        name='deposit-success'
        ),
]+transaction_router.urls