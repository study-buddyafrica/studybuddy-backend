from rest_framework.routers import DefaultRouter
from django.urls import path
from . views  import DepositAPIView, IntaSendWebhookView,deposit_success_view, WalletViewSet, TransactionViewSet

transaction_router = DefaultRouter()

transaction_router.register(r'transactions',TransactionViewSet)
transaction_router.register(r'wallet',WalletViewSet)


urlpatterns = [
    path("wallet/deposit/", DepositAPIView.as_view(), name="wallet-deposit"),
    path('webhooks/intasend/', IntaSendWebhookView.as_view(), name='intasend-webhook'),
    
    # Success page (for redirect)
    path('deposit/success/', deposit_success_view, name='deposit-success'),
]+transaction_router.urls