from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (SpectacularAPIView, 
    SpectacularSwaggerView, SpectacularRedocView)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'),
         name='swagger-ui'),
    path('api/schema/redoc/',
         SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('admin/', admin.site.urls),
    path('api/',include('apps.core.urls')),
    path('api/', include('apps.users.urls')),
    path('api/',include('apps.school.urls')),
    path('api/',include('apps.transactions.urls'))
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
