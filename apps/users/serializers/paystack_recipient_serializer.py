from rest_framework import serializers


class PaystackRecipientSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=50, write_only=True)
    bank_code = serializers.CharField(max_length=20, write_only=True, default="MPESA")
    currency = serializers.CharField(max_length=3, default="KES")
    recipient_type = serializers.CharField(max_length=30, default="mobile_money")

    def validate_account_number(self, value):
        value = value.strip()
        # Validate Kenyan phone number format: 254XXXXXXXXX
        if not value.startswith("254"):
            raise serializers.ValidationError("Phone number must be in Kenyan format: 254XXXXXXXXX")
        if len(value) != 12:
            raise serializers.ValidationError("Phone number must be 12 digits (254XXXXXXXXX).")
        if not value[3:].isdigit():
            raise serializers.ValidationError("Phone number must contain digits only after country code.")
        return value

    def validate_bank_code(self, value):
        value = value.strip().upper()
        if value != "MPESA":
            raise serializers.ValidationError("Bank code must be 'MPESA' for Kenyan mobile money.")
        return value

    def validate_currency(self, value):
        value = value.upper()
        if value != "KES":
            raise serializers.ValidationError("Currency must be 'KES' for Kenya.")
        return value
