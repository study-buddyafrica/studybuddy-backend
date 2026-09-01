from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from apps.core.auth.serializers.auth_serializer import (
    CustomTokenObtainPairSerializer,
    CheckUserSerializer,
)


class AuthThrottle(AnonRateThrottle):
    """Rate limit authentication endpoints to 5 attempts per minute."""
    scope = "login"


class CustomObtainTokenPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AuthThrottle]


class CheckUserView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CheckUserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)
