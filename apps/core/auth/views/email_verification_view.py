from rest_framework import generics, status, permissions
from rest_framework.response import Response
from apps.core.auth.serializers.email_verification_serializer import EmailVerificationSerializer
from apps.core.utils.email_verification import send_verification_email
from apps.core.models import EmailVerificationCode

class RequestEmailVerificationView(generics.GenericAPIView):
    """
    POST: Send verification code to logged-in user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.account_confirmed:
            return Response(
                {"detail": "Your email is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        recent_code = EmailVerificationCode.objects.filter(user=user).order_by("-created_at").first()
        if recent_code and not recent_code.is_expired():
            return Response(
                {"detail": "Verification code already sent. Try again after 10 minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        send_verification_email(user)
        return Response(
            {"message": "Verification code sent successfully to your email."},
            status=status.HTTP_200_OK,
        )


class VerifyEmailView(generics.GenericAPIView):
    """
    POST: Verify email with code
    """
    serializer_class = EmailVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        return Response(response, status=status.HTTP_200_OK)
