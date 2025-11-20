from rest_framework import status, generics
from rest_framework.response import Response

from apps.core.auth.serializers.reset_password_serializer import (
    RequestPasswordResetSerializer,
    ConfirmPasswordResetSerializer
)

class RequestPasswordResetView(generics.GenericAPIView):
    serializer_class = RequestPasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "If this email exists, "
            "a reset code has been sent."
            },
            status=status.HTTP_200_OK
        )


class ConfirmPasswordResetView(generics.GenericAPIView):
    serializer_class = ConfirmPasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password reset successful."},
            status=status.HTTP_200_OK
        )
