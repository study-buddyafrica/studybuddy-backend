from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.core.auth.serializers.reset_password_serializer import (
    RequestPasswordResetSerializer,
    ConfirmPasswordResetSerializer
)

class RequestPasswordResetView(generics.GenericAPIView):
    serializer_class = RequestPasswordResetSerializer
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password reset successful."},
            status=status.HTTP_200_OK
        )


class ResetPasswordCompatibilityView(generics.GenericAPIView):
    """Accept either reset request payload or confirm payload on the same endpoint."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        confirm_fields = {"code", "new_password", "confirm_password"}

        if confirm_fields.intersection(data.keys()):
            serializer = ConfirmPasswordResetSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"message": "Password reset successful."},
                status=status.HTTP_200_OK,
            )

        serializer = RequestPasswordResetSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "If this email exists, a reset code has been sent."},
            status=status.HTTP_200_OK,
        )
