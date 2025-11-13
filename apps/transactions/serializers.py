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
            raise serializers.ValidationError("System wallet cannot be created or modified via API. Only one system wallet linked to a superuser is allowed.")
        elif not user:
            raise serializers.ValidationError(f"{account_type.capitalize()} wallet must be linked to a user.")

        return attrs
  
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'