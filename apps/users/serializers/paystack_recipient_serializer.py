from rest_framework import serializers


class PaystackRecipientSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=50, write_only=True)
    bank_code = serializers.CharField(max_length=20, write_only=True)
    currency = serializers.CharField(max_length=3, default="KES")
    recipient_type = serializers.CharField(max_length=30, default="nuban")

    def validate_account_number(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError("Account number must contain digits only.")
        return value

    def validate_bank_code(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Bank code is required.")
        return value

    def validate_currency(self, value):
        return value.upper()
