
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (SpectacularAPIView, 
    SpectacularSwaggerView, SpectacularRedocView)
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'),
         name='swagger-ui'),
    path('api/schema/redoc/',
         SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('admin/', admin.site.urls),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
