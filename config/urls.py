from datetime import datetime

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from django.conf import settings
from django.conf.urls.static import static
from apps.users.views.profile_views import (
    ParentRegisterStudentView,
    ParentChildrenView,
    ParentFullProfileView,
)
from apps.core.auth.views.reset_password_view import (
    RequestPasswordResetView,
    ConfirmPasswordResetView,
    VerifyPasswordResetCodeView,
    ResetPasswordCompatibilityView,
)
from apps.core.auth.views.auth_views import CheckUserView
from apps.core.views.admin_views import get_classes, get_subjects, admin_dashboard_stats
from apps.school.views.performance_compatibility_views import (
    StudentPerformanceView,
    CompletedLessonsView,
    SubmitTimeRangeView,
    AvailableTimesView,
)
from apps.school.views.teacher_videos_view import TeacherVideosView
from apps.school.views.teacher_live_lessons_view import TeacherLiveLessonsView
from apps.transactions.views.wallet_view import CurrentWalletView


urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("studybuddy-admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.school.urls")),
    path("api/", include("apps.transactions.urls")),
    path("api/", include("apps.calendar.urls")),
    # Auth compatibility routes
    path(
        "auth/forgot-password",
        RequestPasswordResetView.as_view(),
        name="auth-forgot-password-no-slash",
    ),
    path(
        "auth/check_user",
        CheckUserView.as_view(),
        name="auth-check-user-no-slash",
    ),
    path(
        "auth/check_user/",
        CheckUserView.as_view(),
        name="auth-check-user",
    ),
    path(
        "auth/forgot-password/",
        RequestPasswordResetView.as_view(),
        name="auth-forgot-password",
    ),
    path(
        "auth/reset-password",
        ResetPasswordCompatibilityView.as_view(),
        name="auth-reset-password-no-slash",
    ),
    path(
        "auth/reset-password/",
        ResetPasswordCompatibilityView.as_view(),
        name="auth-reset-password",
    ),
    path(
        "auth/reset-password/confirm",
        ConfirmPasswordResetView.as_view(),
        name="auth-reset-password-confirm-no-slash",
    ),
    path(
        "auth/reset-password/confirm/",
        ConfirmPasswordResetView.as_view(),
        name="auth-reset-password-confirm",
    ),
    path(
        "auth/reset-password/verify",
        VerifyPasswordResetCodeView.as_view(),
        name="auth-reset-password-verify-no-slash",
    ),
    path(
        "auth/reset-password/verify/",
        VerifyPasswordResetCodeView.as_view(),
        name="auth-reset-password-verify",
    ),
    path(
        "api/auth/forgot-password",
        RequestPasswordResetView.as_view(),
        name="api-auth-forgot-password-no-slash",
    ),
    path(
        "api/auth/check_user",
        CheckUserView.as_view(),
        name="api-auth-check-user-no-slash",
    ),
    path(
        "api/auth/check_user/",
        CheckUserView.as_view(),
        name="api-auth-check-user",
    ),
    path(
        "api/auth/forgot-password/",
        RequestPasswordResetView.as_view(),
        name="api-auth-forgot-password",
    ),
    path(
        "api/auth/reset-password",
        ResetPasswordCompatibilityView.as_view(),
        name="api-auth-reset-password-no-slash",
    ),
    path(
        "api/auth/reset-password/",
        ResetPasswordCompatibilityView.as_view(),
        name="api-auth-reset-password",
    ),
    path(
        "api/auth/reset-password/confirm",
        ConfirmPasswordResetView.as_view(),
        name="api-auth-reset-password-confirm-no-slash",
    ),
    path(
        "api/auth/reset-password/confirm/",
        ConfirmPasswordResetView.as_view(),
        name="api-auth-reset-password-confirm",
    ),
    path(
        "api/auth/reset-password/verify",
        VerifyPasswordResetCodeView.as_view(),
        name="api-auth-reset-password-verify-no-slash",
    ),
    path(
        "api/auth/reset-password/verify/",
        VerifyPasswordResetCodeView.as_view(),
        name="api-auth-reset-password-verify",
    ),
    # Root admin compatibility routes used by frontend
    path("admin/get-classes", get_classes, name="root-admin-get-classes-no-slash"),
    path("admin/get-classes/", get_classes, name="root-admin-get-classes"),
    path("admin/get-subjects", get_subjects, name="root-admin-get-subjects-no-slash"),
    path("admin/get-subjects/", get_subjects, name="root-admin-get-subjects"),
    path(
        "admin/dashboard-stats",
        admin_dashboard_stats,
        name="root-admin-dashboard-stats-no-slash",
    ),
    path(
        "admin/dashboard-stats/",
        admin_dashboard_stats,
        name="root-admin-dashboard-stats",
    ),
    # Performance and lessons compatibility routes used by frontend
    path(
        "performance/api/student-performance/<str:student_id>",
        StudentPerformanceView.as_view(),
        name="performance-student-no-slash",
    ),
    path(
        "performance/api/student-performance/<str:student_id>/",
        StudentPerformanceView.as_view(),
        name="performance-student",
    ),
    path(
        "lessons/api/completed-lessons/<str:student_id>",
        CompletedLessonsView.as_view(),
        name="completed-lessons-no-slash",
    ),
    path(
        "lessons/api/completed-lessons/<str:student_id>/",
        CompletedLessonsView.as_view(),
        name="completed-lessons",
    ),
    path(
        "lessons/api/submit-time-range/<str:item_id>",
        SubmitTimeRangeView.as_view(),
        name="submit-time-range-no-slash",
    ),
    path(
        "lessons/api/submit-time-range/<str:item_id>/",
        SubmitTimeRangeView.as_view(),
        name="submit-time-range",
    ),
    path(
        "lessons/api/get-available-times/<str:teacher_id>",
        AvailableTimesView.as_view(),
        name="get-available-times-no-slash",
    ),
    path(
        "lessons/api/get-available-times/<str:teacher_id>/",
        AvailableTimesView.as_view(),
        name="get-available-times",
    ),
    path(
        "lessons/api/videos/teacher/<str:teacher_id>",
        TeacherVideosView.as_view(),
        name="teacher-videos-no-slash",
    ),
    path(
        "lessons/api/videos/teacher/<str:teacher_id>/",
        TeacherVideosView.as_view(),
        name="teacher-videos",
    ),
    path(
        "api/performance/api/student-performance/<str:student_id>",
        StudentPerformanceView.as_view(),
        name="api-performance-student-no-slash",
    ),
    path(
        "api/performance/api/student-performance/<str:student_id>/",
        StudentPerformanceView.as_view(),
        name="api-performance-student",
    ),
    path(
        "api/lessons/api/completed-lessons/<str:student_id>",
        CompletedLessonsView.as_view(),
        name="api-completed-lessons-no-slash",
    ),
    path(
        "api/lessons/api/completed-lessons/<str:student_id>/",
        CompletedLessonsView.as_view(),
        name="api-completed-lessons",
    ),
    path(
        "api/lessons/api/submit-time-range/<str:item_id>",
        SubmitTimeRangeView.as_view(),
        name="api-submit-time-range-no-slash",
    ),
    path(
        "api/lessons/api/submit-time-range/<str:item_id>/",
        SubmitTimeRangeView.as_view(),
        name="api-submit-time-range",
    ),
    path(
        "api/lessons/api/get-available-times/<str:teacher_id>",
        AvailableTimesView.as_view(),
        name="api-get-available-times-no-slash",
    ),
    path(
        "api/lessons/api/get-available-times/<str:teacher_id>/",
        AvailableTimesView.as_view(),
        name="api-get-available-times",
    ),
    path(
        "api/lessons/api/videos/teacher/<str:teacher_id>",
        TeacherVideosView.as_view(),
        name="api-teacher-videos-no-slash",
    ),
    path(
        "api/lessons/api/videos/teacher/<str:teacher_id>/",
        TeacherVideosView.as_view(),
        name="api-teacher-videos",
    ),
    path(
        "teacher/live-lessons",
        TeacherLiveLessonsView.as_view(),
        name="teacher-live-lessons-no-slash",
    ),
    path(
        "teacher/live-lessons/",
        TeacherLiveLessonsView.as_view(),
        name="teacher-live-lessons",
    ),
    path(
        "api/teacher/live-lessons",
        TeacherLiveLessonsView.as_view(),
        name="api-teacher-live-lessons-no-slash",
    ),
    path(
        "api/teacher/live-lessons/",
        TeacherLiveLessonsView.as_view(),
        name="api-teacher-live-lessons",
    ),
    path(
        "payments/wallet/<str:wallet_id>",
        CurrentWalletView.as_view(),
        name="payments-wallet-no-slash",
    ),
    path(
        "payments/wallet/<str:wallet_id>/",
        CurrentWalletView.as_view(),
        name="payments-wallet",
    ),
    path(
        "api/payments/wallet/<str:wallet_id>",
        CurrentWalletView.as_view(),
        name="api-payments-wallet-no-slash",
    ),
    path(
        "api/payments/wallet/<str:wallet_id>/",
        CurrentWalletView.as_view(),
        name="api-payments-wallet",
    ),
    # Legacy frontend compatibility routes (without /api prefix)
    path(
        "users/parent/register-student",
        ParentRegisterStudentView.as_view(),
        name="users-parent-register-student-no-slash",
    ),
    path(
        "users/parent/register-student/",
        ParentRegisterStudentView.as_view(),
        name="users-parent-register-student",
    ),
    path(
        "users/parent/profile/full",
        ParentFullProfileView.as_view(),
        name="users-parent-full-profile-no-slash",
    ),
    path(
        "users/parent/profile/full/",
        ParentFullProfileView.as_view(),
        name="users-parent-full-profile",
    ),
    path(
        "users/parent/<str:parent_id>/students",
        ParentChildrenView.as_view(),
        name="users-parent-students-no-slash",
    ),
    path(
        "users/parent/<str:parent_id>/students/",
        ParentChildrenView.as_view(),
        name="users-parent-students",
    ),
    path(
        "",
        lambda request: JsonResponse(
            {"message": "Welcome to StudyBuddy API", "time": datetime.now().isoformat()}
        ),
    ),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
