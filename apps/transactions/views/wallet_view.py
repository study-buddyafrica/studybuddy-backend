from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Prefetch

from apps.core.permissions import IsAdminOrReadOnly
from apps.transactions.models import Wallet
from apps.transactions.serializers.wallet_serializer import WalletSerializer


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Wallet rules:
    - Wallets created automatically via signals (no POST)
    - Users may only view their wallet(s)
    - Admins may update/deactivate wallets
    - No DELETE allowed (admin can disable instead)
    """

    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrReadOnly
    ]

    def get_queryset(self):
        user = self.request.user

        qs = Wallet.objects.select_related("user").only(
            "id", "user", "account_type", "balance", 
            "is_active", "failed_withdraw_attempts", "created_at", "updated_at"
        )

        if user.is_superuser:
            return qs

        return qs.filter(user=user)

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Wallets are created automatically."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only admins can update wallet data."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only admins can update wallet data."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Wallets cannot be deleted. Admins may deactivate instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class CurrentWalletView(APIView):
    """Compatibility endpoint for frontend wallet lookups with optional undefined IDs."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, wallet_id=None):
        if wallet_id in (None, "", "undefined", "null"):
            wallet = Wallet.objects.filter(user=request.user).first()
            if not wallet:
                return Response({"detail": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)

        wallet = Wallet.objects.filter(id=wallet_id).first()
        if not wallet:
            return Response({"detail": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_superuser and wallet.user != request.user:
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)

        return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)
