from rest_framework import serializers
from django.core.exceptions import ValidationError

from apps.transactions.models import Transaction, Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'

    
    def validate(self, attrs):
        account_type = attrs.get("account_type")
        user = attrs.get("user")

        if account_type == "system":
            if self.instance is None and Wallet.objects.filter(account_type="system").exists():
                raise serializers.ValidationError("Only one system wallet is allowed.")
            if user is not None:
                raise serializers.ValidationError("System wallet cannot be linked to a user.")
        else:
            if user is None:
                raise serializers.ValidationError(f"{account_type.capitalize()} wallet must have a linked user.")

        return attrs

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'