from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.auth.views.auth_views import CustomObtainTokenPairView
from apps.core.auth.views.google_auth_view import GoogleOAuthConnectView
from apps.core.auth.views.email_verification_view import (
    RequestRegistrationVerificationCode,
    VerifyRegistrationEmailView,
)
from apps.core.auth.views.reset_password_view import (
    RequestPasswordResetView,
    ConfirmPasswordResetView
)

urlpatterns = [
    path(
        "token/refresh/", 
        TokenRefreshView.as_view(), 
        name="token_refresh"
    ),
    path("token/request/",
         CustomObtainTokenPairView.as_view(), 
         name="token_request"
        ),
    path(
        "verify-email/request/", 
        RequestRegistrationVerificationCode.as_view(), 
        name="email-verification-request"
    ),
    path(
        "verify-email/confirm/", 
        VerifyRegistrationEmailView.as_view(), 
        name="email-verification-confirm"
    ),
    path(
        "teacher/google/connect/", 
        GoogleOAuthConnectView.as_view(), 
        name="teacher-google-connect"
    ),
    path(
        "password/reset/request/", 
        RequestPasswordResetView.as_view(), 
        name="password-reset-request"
    ),
    path(
        "password/reset/confirm/", 
        ConfirmPasswordResetView.as_view(), 
        name="password-reset-confirm"
    ),

]
