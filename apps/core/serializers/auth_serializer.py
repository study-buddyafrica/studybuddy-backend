from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.core.models import User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['is_superuser'] = user.is_superuser
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['role'] = getattr(user, "role", None)

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        user_data = {
            "id": self.user.id,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "role": getattr(self.user, "role", None),
            "is_superuser": self.user.is_superuser,
        }

        data.update({"user": user_data})
        return data
