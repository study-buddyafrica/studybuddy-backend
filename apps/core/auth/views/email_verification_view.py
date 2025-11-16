from rest_framework import generics
from rest_framework.response import Response
from apps.core.auth.serializers.email_verification_serializer import (
    PreRegistrationVerifySerializer,
    PreRegisterEmailSerializer
)

class RequestRegistrationVerificationCode(generics.GenericAPIView):
    serializer_class = PreRegisterEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=200)


class VerifyRegistrationEmailView(generics.GenericAPIView):
    serializer_class = PreRegistrationVerifySerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=200)
