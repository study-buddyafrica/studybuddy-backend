from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.utils._os import safe_join
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsTeacherOrAdmin, IsVerified, IsStudent
from apps.core.utils.media_hls import HlsMediaPipelineService
from apps.core.utils.signed_tokens import SignedTokenService
from apps.core.utils.zoom_sdk import ZoomSDKTokenService
from apps.school.models import CourseEnrollment, LiveSession, PeerSession
from apps.school.models import Course
from apps.users.models import StudentProfile


def _build_hls_download_url(
    request, relative_path: str, ttl_seconds: int | None = None
) -> str:
    service = HlsMediaPipelineService()
    token = service.create_download_token(relative_path, ttl_seconds=ttl_seconds)
    relative_url = f"{reverse('hls-media-download')}?path={quote(relative_path)}&token={quote(token)}"
    return request.build_absolute_uri(relative_url)


class HlsTranscodeView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, IsTeacherOrAdmin]

    def post(self, request):
        uploaded_video = request.FILES.get("video")
        if not uploaded_video:
            return Response(
                {"error": "video file is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        service = HlsMediaPipelineService()
        source_dir = Path(settings.MEDIA_ROOT) / "hls" / "uploads"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = (
            source_dir / f"{Path(uploaded_video.name).stem}_{uuid.uuid4().hex}.mp4"
        )
        with open(source_path, "wb") as target_file:
            for chunk in uploaded_video.chunks():
                target_file.write(chunk)

        pipeline = service.transcode(
            source_path=source_path,
            asset_id=request.data.get("asset_id"),
            download_url_builder=lambda relative_path: _build_hls_download_url(
                request, relative_path
            ),
            segment_time=int(request.data.get("segment_time", 6)),
        )

        manifest_url = _build_hls_download_url(
            request,
            service.relative_path(pipeline["manifest_path"]),
            ttl_seconds=settings.HLS_URL_TTL_SECONDS,
        )
        segment_urls = [
            _build_hls_download_url(request, service.relative_path(segment_path))
            for segment_path in pipeline["segment_files"]
        ]
        key_url = None
        if pipeline.get("key_file_path"):
            key_url = _build_hls_download_url(
                request, service.relative_path(pipeline["key_file_path"])
            )

        return Response(
            {
                "asset_id": pipeline["asset_id"],
                "manifest_url": manifest_url,
                "segment_urls": segment_urls,
                "encryption_key_url": key_url,
                "expires_in": settings.HLS_URL_TTL_SECONDS,
            },
            status=status.HTTP_201_CREATED,
        )


class HlsOfflineTokenView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, IsTeacherOrAdmin]

    def post(self, request):
        asset_id = request.data.get("asset_id")
        if not asset_id:
            return Response(
                {"error": "asset_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        service = HlsMediaPipelineService()
        try:
            relative_paths = service.list_downloadable_relative_paths(asset_id)
        except FileNotFoundError:
            raise Http404("HLS asset not found")

        manifest_relative = next(
            (
                relative_path
                for relative_path in relative_paths
                if relative_path.endswith("playlist.m3u8")
            ),
            None,
        )
        download_urls = [
            _build_hls_download_url(request, relative_path)
            for relative_path in relative_paths
        ]
        manifest_url = (
            _build_hls_download_url(request, manifest_relative)
            if manifest_relative
            else None
        )

        return Response(
            {
                "asset_id": asset_id,
                "manifest_url": manifest_url,
                "download_urls": download_urls,
                "expires_in": settings.HLS_URL_TTL_SECONDS,
            },
            status=status.HTTP_200_OK,
        )


class HlsDownloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        relative_path = request.query_params.get("path")
        token = request.query_params.get("token")

        if not relative_path or not token:
            return Response(
                {"error": "path and token are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = HlsMediaPipelineService()
        try:
            service.verify_download_token(token, relative_path)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        try:
            absolute_path = Path(safe_join(str(service.storage_root), relative_path))
        except Exception:
            return Response(
                {"error": "invalid path"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not absolute_path.exists() or not absolute_path.is_file():
            raise Http404("HLS file not found")

        return FileResponse(
            open(absolute_path, "rb"), as_attachment=False, filename=absolute_path.name
        )


class ZoomSDKTokenView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        meeting_number = request.data.get("meeting_number")
        role = int(request.data.get("role", 0))
        user_name = (
            request.data.get("user_name")
            or request.user.get_full_name()
            or request.user.email
        )
        live_session_id = request.data.get("live_session_id")

        if not meeting_number:
            return Response(
                {"error": "meeting_number is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if live_session_id:
            live_session = get_object_or_404(
                LiveSession.objects.select_related(
                    "teacher__user", "session__student__user"
                ),
                id=live_session_id,
            )

            is_allowed = False
            if request.user.is_staff or request.user.is_superuser:
                is_allowed = True
            elif (
                hasattr(request.user, "teacher_profile")
                and live_session.teacher_id == request.user.teacher_profile.id
            ):
                is_allowed = True
            elif (
                hasattr(request.user, "student_profile")
                and live_session.session
                and live_session.session.student_id == request.user.student_profile.id
            ):
                is_allowed = True

            if not is_allowed:
                return Response(
                    {"error": "not allowed for this live session"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        token_service = ZoomSDKTokenService()
        token_data = token_service.generate_signature(
            meeting_number=str(meeting_number),
            role=role,
            user_identity=str(request.user.id),
            user_name=user_name,
        )

        return Response(
            {
                "meeting_number": str(meeting_number),
                "role": role,
                "user_name": user_name,
                "signature": token_data["signature"],
                "mock_mode": token_data["mock_mode"],
                "expires_at": token_data["expires_at"],
            },
            status=status.HTTP_200_OK,
        )


class PeerSessionSignalView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, IsStudent]

    def post(self, request):
        course_id = request.data.get("course_id")
        peer_student_id = request.data.get("peer_student_id")

        if not course_id or not peer_student_id:
            return Response(
                {"error": "course_id and peer_student_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course = get_object_or_404(Course, id=course_id)
        initiator = request.user.student_profile
        peer_student = get_object_or_404(StudentProfile, id=peer_student_id)

        if not CourseEnrollment.objects.filter(
            course=course, student=initiator, is_active=True
        ).exists():
            return Response(
                {"error": "initiator must be actively enrolled in the course"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not CourseEnrollment.objects.filter(
            course=course, student=peer_student, is_active=True
        ).exists():
            return Response(
                {"error": "peer student must be actively enrolled in the course"},
                status=status.HTTP_403_FORBIDDEN,
            )

        peer_session, _ = PeerSession.objects.get_or_create(
            initiator=initiator,
            peer=peer_student,
            course=course,
            defaults={"meeting_link": ""},
        )

        signer = SignedTokenService(
            secret=getattr(settings, "PEER_SESSION_SIGNING_SECRET", None)
            or settings.SECRET_KEY,
            default_ttl_seconds=settings.PEER_SESSION_TOKEN_TTL_SECONDS,
            namespace="peer-session",
        )
        signal_token = signer.issue(
            {
                "peer_session_id": str(peer_session.id),
                "course_id": str(course.id),
                "initiator_id": str(initiator.id),
                "peer_id": str(peer_student.id),
            }
        )

        meeting_link = f"{settings.PEER_SESSION_BASE_URL.rstrip('/')}/{peer_session.id}?token={signal_token}"
        if peer_session.meeting_link != meeting_link:
            peer_session.meeting_link = meeting_link
            peer_session.save(update_fields=["meeting_link"])

        return Response(
            {
                "peer_session_id": str(peer_session.id),
                "signal_token": signal_token,
                "meeting_link": meeting_link,
                "signal_channel": f"peer-session:{peer_session.id}",
            },
            status=status.HTTP_201_CREATED,
        )
