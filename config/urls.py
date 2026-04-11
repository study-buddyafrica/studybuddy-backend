from datetime import datetime

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from drf_spectacular.views import (SpectacularAPIView, 
    SpectacularSwaggerView, SpectacularRedocView)
from django.conf import settings
from django.conf.urls.static import static
from apps.users.views.profile_views import ParentRegisterStudentView, ParentChildrenView
from apps.core.auth.views.reset_password_view import RequestPasswordResetView
from apps.core.views.admin_views import get_classes, get_subjects
from apps.school.views.performance_compatibility_views import (
    StudentPerformanceView,
    CompletedLessonsView,
)


urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'),
         name='swagger-ui'),
    path('api/schema/redoc/',
         SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('studybuddy-admin/', admin.site.urls),
    path('api/',include('apps.core.urls')),
    path('api/', include('apps.users.urls')),
    path('api/',include('apps.school.urls')),
    path('api/',include('apps.transactions.urls')),
    # Auth compatibility routes
    path('auth/forgot-password', RequestPasswordResetView.as_view(), name='auth-forgot-password-no-slash'),
    path('auth/forgot-password/', RequestPasswordResetView.as_view(), name='auth-forgot-password'),
    path('api/auth/forgot-password', RequestPasswordResetView.as_view(), name='api-auth-forgot-password-no-slash'),
    path('api/auth/forgot-password/', RequestPasswordResetView.as_view(), name='api-auth-forgot-password'),
    # Root admin compatibility routes used by frontend
    path('admin/get-classes', get_classes, name='root-admin-get-classes-no-slash'),
    path('admin/get-classes/', get_classes, name='root-admin-get-classes'),
    path('admin/get-subjects', get_subjects, name='root-admin-get-subjects-no-slash'),
    path('admin/get-subjects/', get_subjects, name='root-admin-get-subjects'),
    # Performance and lessons compatibility routes used by frontend
    path('performance/api/student-performance/<str:student_id>', StudentPerformanceView.as_view(), name='performance-student-no-slash'),
    path('performance/api/student-performance/<str:student_id>/', StudentPerformanceView.as_view(), name='performance-student'),
    path('lessons/api/completed-lessons/<str:student_id>', CompletedLessonsView.as_view(), name='completed-lessons-no-slash'),
    path('lessons/api/completed-lessons/<str:student_id>/', CompletedLessonsView.as_view(), name='completed-lessons'),
    path('api/performance/api/student-performance/<str:student_id>', StudentPerformanceView.as_view(), name='api-performance-student-no-slash'),
    path('api/performance/api/student-performance/<str:student_id>/', StudentPerformanceView.as_view(), name='api-performance-student'),
    path('api/lessons/api/completed-lessons/<str:student_id>', CompletedLessonsView.as_view(), name='api-completed-lessons-no-slash'),
    path('api/lessons/api/completed-lessons/<str:student_id>/', CompletedLessonsView.as_view(), name='api-completed-lessons'),
    # Legacy frontend compatibility routes (without /api prefix)
    path('users/parent/register-student', ParentRegisterStudentView.as_view(), name='users-parent-register-student-no-slash'),
    path('users/parent/register-student/', ParentRegisterStudentView.as_view(), name='users-parent-register-student'),
    path('users/parent/<str:parent_id>/students', ParentChildrenView.as_view(), name='users-parent-students-no-slash'),
    path('users/parent/<str:parent_id>/students/', ParentChildrenView.as_view(), name='users-parent-students'),
    path("", lambda request: JsonResponse({
    "message": "Welcome to StudyBuddy API",
    "time": datetime.now().isoformat()
    })),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
