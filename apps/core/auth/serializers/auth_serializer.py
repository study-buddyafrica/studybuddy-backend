from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["is_superuser"] = user.is_superuser
        token["email"] = user.email
        token["first_name"] = user.first_name
        token["role"] = getattr(user, "role", None)
        token["profile_id"] = cls.get_profile_id(user)

        return token

    @staticmethod
    def get_profile_id(user):
        """Return the related profile ID depending on user role."""
        if hasattr(user, "teacher_profile"):
            return str(user.teacher_profile.id)

        if hasattr(user, "parent_profile"):
            return str(user.parent_profile.id)

        if hasattr(user, "student_profile"):
            return str(user.student_profile.id)

        return None

    def validate(self, attrs):
        data = super().validate(attrs)

        profile_id = self.get_profile_id(self.user)

        user_data = {
            "id": self.user.id,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "role": getattr(self.user, "role", None),
            "is_superuser": self.user.is_superuser,
            "profile_id": profile_id,
        }

        data.update({"user": user_data})
        return data
