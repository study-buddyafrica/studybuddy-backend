from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.transactions  .models import Wallet
from apps.transactions.serializers.wallet_serializer import WalletSerializer


class WalletViewSet(viewsets.ModelViewSet):
    permission_classes =[IsAuthenticated]
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()