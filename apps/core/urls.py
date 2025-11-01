from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from apps.core.views.auth_views import CustomObtainTokenPairView

urlspatterns = [
    path("token/request/", CustomObtainTokenPairView.as_view(), name="token_request"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]