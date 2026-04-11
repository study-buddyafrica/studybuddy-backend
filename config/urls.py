from datetime import datetime

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from drf_spectacular.views import (SpectacularAPIView, 
    SpectacularSwaggerView, SpectacularRedocView)
from django.conf import settings
from django.conf.urls.static import static
from apps.users.views.profile_views import ParentRegisterStudentView, ParentChildrenView


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
