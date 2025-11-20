from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsVerified
from apps.transactions .models import Transaction
from apps.transactions.serializers.transaction_serializer import TransactionSerializer


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    - Users: read-only, only their wallet transactions
    - Admins: view all, delete allowed
    """

    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def get_queryset(self):
        user = self.request.user

        qs = (
            Transaction.objects
            .select_related("wallet", "wallet__user")
            .only(
                "id", "transaction_identifier", "amount_currency", "transaction_type",
                "payment_method", "status", "account_number", "description",
                "metadata_info", "timestamp", "related_transaction",
                "wallet__id", "wallet__account_type", "wallet__balance",
                "wallet__is_active", "wallet__user__id",
                "wallet__user__first_name", "wallet__user__last_name",
                "wallet__user__email", "wallet__user__role"
            )
        )

        if user.is_superuser:
            return qs
        return qs.filter(wallet__user=user)

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Transactions cannot be created manually."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Transactions cannot be updated."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Transactions cannot be updated."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only admins can delete transactions."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


