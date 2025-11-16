from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.core.auth.serializers.email_verification_serializer import (
    VerifyPreRegistrationSerializer,
    PreRegisterEmailSerializer
)

class RequestRegistrationVerificationCode(generics.GenericAPIView):
    serializer_class = PreRegisterEmailSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)


class VerifyRegistrationEmailView(generics.GenericAPIView):
    serializer_class = VerifyPreRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)
