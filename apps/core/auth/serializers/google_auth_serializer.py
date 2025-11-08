from rest_framework import serializers

class GoogleOAuthSerializer(serializers.Serializer):
    code = serializers.CharField()
