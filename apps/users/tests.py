from rest_framework import status
from rest_framework.test import APITestCase

from apps.school.models import EducationLevel
from apps.users.models import StudentProfile


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
