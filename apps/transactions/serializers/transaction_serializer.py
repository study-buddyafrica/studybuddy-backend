from rest_framework import serializers
from apps.transactions.models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    wallet = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_identifier",
            "amount_currency",
            "transaction_type",
            "payment_method",
            "status",
            "account_number",
            "description",
            "metadata_info",
            "timestamp",
            "related_transaction",
            "wallet",
            "user",
        ]

    def get_user(self, obj):
        if not obj.wallet or not obj.wallet.user:
            return None
        u = obj.wallet.user
        return {
            "id": str(u.id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "role": u.role,
        }
    
    def _money_field_to_dict(wallet, field):
        amount = getattr(wallet, field, None)
        currency = getattr(wallet, f"{field}_currency", None)
        return {"amount": str(amount), "currency": currency}


    def get_wallet(self, obj):
        if not obj.wallet:
            return None
        w = obj.wallet
        return {
        "account_type": w.account_type,
        "is_active": w.is_active,
        }
