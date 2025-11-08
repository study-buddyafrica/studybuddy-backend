from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from apps.core.auth.views.auth_views import CustomObtainTokenPairView
from apps.core.auth.views.email_verification_view import RequestEmailVerificationView,VerifyEmailView
from apps.core.auth.views.google_auth_view import GoogleOAuthConnectView


urlpatterns = [
    path("token/request/", CustomObtainTokenPairView.as_view(), name="token_request"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify-email/request/", RequestEmailVerificationView.as_view(), name="email-verification-request"),
    path("verify-email/confirm/", VerifyEmailView.as_view(), name="email-verification-confirm"),
    path("teacher/google/connect/", GoogleOAuthConnectView.as_view(), name="teacher-google-connect"),
]