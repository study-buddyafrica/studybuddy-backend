from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.transactions  .models import Transaction
from apps.transactions.serializers import TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes =[IsAuthenticated]
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

