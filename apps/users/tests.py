from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from djmoney.money import Money

from apps.school.models import EducationLevel
from apps.users.models import StudentProfile, TeacherProfile

User = get_user_model()


class UserRegistrationEducationLevelTests(APITestCase):
    def setUp(self):
        self.k12, _ = EducationLevel.objects.update_or_create(
            code=EducationLevel.AudienceTier.K12,
            defaults={
                "name": "K-12",
                "description": "Primary and secondary education tracks.",
            },
        )
        self.university, _ = EducationLevel.objects.update_or_create(
            code=EducationLevel.AudienceTier.UNIVERSITY,
            defaults={
                "name": "University",
                "description": "University and higher education tracks.",
            },
        )

    def test_student_registration_accepts_education_level_id(self):
        payload = {
            "email": "student@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "username": "jane-doe",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
            "role": "student",
            "country": "Kenya",
            "education_level_id": str(self.university.id),
        }

        response = self.client.post("/api/users/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        student = StudentProfile.objects.select_related("education_level").get(
            user__email="student@example.com"
        )
        self.assertEqual(student.education_level_id, self.university.id)

    def test_student_registration_defaults_to_k12_when_education_level_missing(self):
        payload = {
            "email": "student2@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "username": "john-doe",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
            "role": "student",
            "country": "Kenya",
        }

        response = self.client.post("/api/users/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        student = StudentProfile.objects.select_related("education_level").get(
            user__email="student2@example.com"
        )
        self.assertEqual(student.education_level_id, self.k12.id)


class TeacherListViewTests(APITestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            email="teacher@example.com",
            first_name="Grace",
            last_name="Otieno",
            username="grace-otieno",
            password="StrongPass123",
            role="teacher",
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user,
            phone="+254700000000",
            hourly_rate=Money(1500, "KES"),
            profile_picture=SimpleUploadedFile(
                "profile.jpg", b"fake-image-data", content_type="image/jpeg"
            ),
            is_verified=True,
        )

    def test_teacher_list_endpoint_returns_hourly_rate(self):
        response = self.client.get("/api/teachers/list?limit=100")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payload = response.data
        results = (
            payload["results"]
            if isinstance(payload, dict) and "results" in payload
            else payload
        )

        self.assertTrue(any(item["id"] == str(self.teacher.id) for item in results))
        teacher_data = next(
            item for item in results if item["id"] == str(self.teacher.id)
        )
        self.assertIn("hourly_rate", teacher_data)
