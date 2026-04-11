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
    ConfirmPasswordResetView,
)
from apps.core.views.health_check_view import DatabaseHealthCheckView
from apps.core.views.admin_views import (
    admin_dashboard_stats,
    admin_get_classes,
    admin_list_users,
    admin_list_teachers,
    admin_list_students,
)

urlpatterns = [
    path("login/", CustomObtainTokenPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "verify-email/request/",
        RequestRegistrationVerificationCode.as_view(),
        name="email-verification-request",
    ),
    path(
        "verify-email/confirm/",
        VerifyRegistrationEmailView.as_view(),
        name="email-verification-confirm",
    ),
    path(
        "teacher/google/connect/",
        GoogleOAuthConnectView.as_view(),
        name="teacher-google-connect",
    ),
    path(
        "password/reset/request/",
        RequestPasswordResetView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        ConfirmPasswordResetView.as_view(),
        name="password-reset-confirm",
    ),
    path("health/", DatabaseHealthCheckView.as_view(), name="database-health-check"),
    # Admin Dashboard Endpoints
    path("admin/dashboard-stats/", admin_dashboard_stats, name="admin-dashboard-stats"),
    path("admin/get-classes/", admin_get_classes, name="admin-get-classes"),
    path("admin/users/", admin_list_users, name="admin-list-users"),
    path("admin/teachers/", admin_list_teachers, name="admin-list-teachers"),
    path("admin/students/", admin_list_students, name="admin-list-students"),
]
