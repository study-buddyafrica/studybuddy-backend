import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from apps.users.models import TeacherProfile
from apps.core.auth.serializers.google_auth_serializer import GoogleOAuthSerializer
from datetime import timedelta

class GoogleOAuthConnectView(generics.GenericAPIView):
    """
    Exchange authorization code for tokens and store them for teacher
    """
    serializer_class = GoogleOAuthSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        user = request.user

        try:
            teacher = user.teacher_profile
        except TeacherProfile.DoesNotExist:
            return Response({"detail": "Teacher profile not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        r = requests.post(token_url, data=payload)
        if r.status_code != 200:
            return Response({"detail": "Failed to get tokens from Google.", "error": r.json()}, status=status.HTTP_400_BAD_REQUEST)

        data = r.json()
        teacher.google_access_token = data['access_token']
        teacher.google_refresh_token = data.get('refresh_token', teacher.google_refresh_token)
        teacher.google_token_expiry = timezone.now() + timedelta(seconds=int(data['expires_in']))
        teacher.save()

        return Response({"detail": "Google account connected successfully."}, status=status.HTTP_200_OK)
