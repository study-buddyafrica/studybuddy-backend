from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from djmoney.money import Money
from rest_framework import status
from rest_framework.test import APITestCase

from apps.school.models import (
    Course,
    CourseEnrollment,
    EducationLevel,
    PeerSession,
    Subject,
)
from apps.users.models import StudentProfile, TeacherProfile

User = get_user_model()


class MediaAndCommunicationViewTests(APITestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.override = override_settings(
            HLS_STORAGE_ROOT=self.temp_dir.name,
            HLS_URL_TTL_SECONDS=900,
            HLS_ENABLE_ENCRYPTION=True,
            PEER_SESSION_TOKEN_TTL_SECONDS=900,
        )
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.temp_dir.cleanup()

    def _fake_ffmpeg_run(self, cmd, check, capture_output, text):
        raw_manifest_path = Path(cmd[-1])
        output_dir = raw_manifest_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "segment_00000.ts").write_bytes(b"segment-0")
        (output_dir / "segment_00001.ts").write_bytes(b"segment-1")
        if "-hls_key_info_file" in cmd:
            (output_dir / "encryption.key").write_bytes(b"0123456789abcdef")
            raw_manifest_path.write_text(
                "#EXTM3U\n"
                "#EXT-X-VERSION:3\n"
                '#EXT-X-KEY:METHOD=AES-128,URI="encryption.key"\n'
                "segment_00000.ts\n"
                "segment_00001.ts\n",
                encoding="utf-8",
            )
        else:
            raw_manifest_path.write_text(
                "#EXTM3U\n#EXT-X-VERSION:3\nsegment_00000.ts\nsegment_00001.ts\n",
                encoding="utf-8",
            )
        return MagicMock(returncode=0)

    def test_hls_transcode_and_download_endpoint(self):
        teacher_user = User.objects.create_user(
            email="teacher-media@example.com",
            first_name="Grace",
            last_name="Otieno",
            username="teacher-media",
            password="StrongPass123",
            role="teacher",
        )
        teacher_user.account_confirmed = True
        teacher_user.save(update_fields=["account_confirmed"])
        TeacherProfile.objects.create(
            user=teacher_user,
            phone="+254700000000",
            hourly_rate=Money(1500, "KES"),
            profile_picture=SimpleUploadedFile(
                "profile.jpg", b"fake-image-data", content_type="image/jpeg"
            ),
            is_verified=True,
        )
        self.client.force_authenticate(teacher_user)

        with patch(
            "apps.core.utils.media_hls.subprocess.run",
            side_effect=self._fake_ffmpeg_run,
        ):
            response = self.client.post(
                "/api/media/hls/transcode/",
                {
                    "video": SimpleUploadedFile(
                        "lesson.mp4", b"fake-mp4-data", content_type="video/mp4"
                    )
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("asset_id", response.data)
        self.assertTrue(response.data["segment_urls"])
        self.assertIn("manifest_url", response.data)
        self.assertIsNotNone(response.data["encryption_key_url"])

        manifest_url = urlparse(response.data["manifest_url"])
        manifest_response = self.client.get(
            manifest_url.path + "?" + manifest_url.query
        )
        self.assertEqual(manifest_response.status_code, status.HTTP_200_OK)
        manifest_body = b"".join(manifest_response.streaming_content)
        self.assertIn(b"segment_00000.ts", manifest_body)
        self.assertIn(b"encryption.key", manifest_body)

        first_segment_url = urlparse(response.data["segment_urls"][0])
        segment_response = self.client.get(
            first_segment_url.path + "?" + first_segment_url.query
        )
        self.assertEqual(segment_response.status_code, status.HTTP_200_OK)
        segment_body = b"".join(segment_response.streaming_content)
        self.assertEqual(segment_body, b"segment-0")

        offline_token_response = self.client.post(
            "/api/media/hls/offline-token/",
            {"asset_id": response.data["asset_id"]},
            format="json",
        )
        self.assertEqual(offline_token_response.status_code, status.HTTP_200_OK)
        self.assertTrue(offline_token_response.data["download_urls"])

    def test_zoom_sdk_token_endpoint_returns_signature(self):
        teacher_user = User.objects.create_user(
            email="zoom-teacher@example.com",
            first_name="Zoom",
            last_name="Teacher",
            username="zoom-teacher",
            password="StrongPass123",
        )
        teacher_user.account_confirmed = True
        teacher_user.save(update_fields=["account_confirmed"])
        self.client.force_authenticate(teacher_user)

        response = self.client.post(
            "/api/live-sessions/zoom/sdk-token/",
            {
                "meeting_number": "123456789",
                "role": 1,
                "user_name": "Zoom Teacher",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["mock_mode"])
        self.assertTrue(response.data["signature"].startswith("mock-zoom-"))

    def test_peer_session_signal_endpoint_creates_room(self):
        teacher_user = User.objects.create_user(
            email="peer-teacher@example.com",
            first_name="Peer",
            last_name="Teacher",
            username="peer-teacher",
            password="StrongPass123",
            role="teacher",
        )
        teacher_user.account_confirmed = True
        teacher_user.save(update_fields=["account_confirmed"])
        teacher_profile = TeacherProfile.objects.create(
            user=teacher_user,
            phone="+254700000001",
            hourly_rate=Money(1000, "KES"),
            profile_picture=SimpleUploadedFile(
                "profile.jpg", b"fake-image-data", content_type="image/jpeg"
            ),
            is_verified=True,
        )

        subject = Subject.objects.create(name="Mathematics")
        course = Course.objects.create(
            subject=subject,
            title="Peer Study Course",
            description="A course for peer learning",
            is_universal=True,
            teacher=teacher_profile,
        )

        initiator_user = User.objects.create_user(
            email="student-one@example.com",
            first_name="Student",
            last_name="One",
            username="student-one",
            password="StrongPass123",
            role="student",
        )
        initiator_user.account_confirmed = True
        initiator_user.save(update_fields=["account_confirmed"])
        initiator_profile = StudentProfile.objects.create(user=initiator_user)

        peer_user = User.objects.create_user(
            email="student-two@example.com",
            first_name="Student",
            last_name="Two",
            username="student-two",
            password="StrongPass123",
            role="student",
        )
        peer_user.account_confirmed = True
        peer_user.save(update_fields=["account_confirmed"])
        peer_profile = StudentProfile.objects.create(user=peer_user)

        CourseEnrollment.objects.create(
            course=course, student=initiator_profile, is_active=True
        )
        CourseEnrollment.objects.create(
            course=course, student=peer_profile, is_active=True
        )

        self.client.force_authenticate(initiator_user)
        response = self.client.post(
            "/api/peer-sessions/signal/",
            {"course_id": str(course.id), "peer_student_id": str(peer_profile.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("signal_token", response.data)
        self.assertIn("meeting_link", response.data)
        self.assertIn("token=", response.data["meeting_link"])
        self.assertTrue(
            PeerSession.objects.filter(id=response.data["peer_session_id"]).exists()
        )


class EducationLevelEndpointTests(APITestCase):
    def setUp(self):
        EducationLevel.objects.update_or_create(
            code=EducationLevel.AudienceTier.K12,
            defaults={
                "name": "K-12",
                "description": "Primary and secondary education tracks.",
            },
        )
        EducationLevel.objects.update_or_create(
            code=EducationLevel.AudienceTier.UNIVERSITY,
            defaults={
                "name": "University",
                "description": "University and higher education tracks.",
            },
        )
        EducationLevel.objects.update_or_create(
            code=EducationLevel.AudienceTier.CONTINUOUS,
            defaults={
                "name": "Continuous Learning",
                "description": "Professional and lifelong learning tracks.",
            },
        )

    def test_list_education_levels_is_public_and_returns_levels(self):
        response = self.client.get("/api/education-levels/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = getattr(response, "data", None)
        payload = data.get("results", data) if isinstance(data, dict) else (data or [])
        self.assertGreaterEqual(len(payload), 3)
        codes = {item["code"] for item in payload}
        self.assertTrue({"k12", "university", "continuous"}.issubset(codes))
