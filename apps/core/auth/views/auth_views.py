from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from apps.core.auth.serializers.auth_serializer import CustomTokenObtainPairSerializer

class CustomObtainTokenPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer