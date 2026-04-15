from rest_framework import status
from rest_framework.test import APITestCase

from apps.school.models import EducationLevel


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
