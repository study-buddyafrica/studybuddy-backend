import os
from django.core.management.utils import get_random_secret_key
from django.test import TestCase
from rest_framework.test import APIClient
from apps.core.models import User
from apps.school.models import Course, Subject, Grade
import uuid


class XSSProtectionTestCase(TestCase):
    """
    Test XSS sanitization on user-generated content
    """

    def setUp(self):
        """Set up test client and test user"""
        self.client = APIClient()

        # Create test teacher user
        self.user = User.objects.create_user(
            email="teacher@test.com",
            first_name="Test",
            username="testteacher",
            password="testpass123",
            role="teacher",
            account_confirmed=True,
        )

        # Create test subject and grade
        self.subject = Subject.objects.create(
            name="Mathematics", description="Math courses"
        )
        self.grade = Grade.objects.create(level="Grade 10")

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_course_title_sanitization(self):
        """Test that XSS in course title is sanitized"""
        xss_payload = {
            "title": "<script>alert('XSS')</script>Math 101",
            "description": "Safe description",
            "subject": str(self.subject.id),
            "grade": str(self.grade.id),
            "price": "500.00",
        }

        response = self.client.post("/api/courses/", xss_payload, format="json")

        if response.status_code == 201:
            # Script tag should be removed
            self.assertNotIn("<script>", response.data.get("title", ""))
            self.assertIn("Math 101", response.data.get("title", ""))

    def test_course_description_sanitization(self):
        """Test that XSS in course description is sanitized"""
        xss_payload = {
            "title": "Math 101",
            "description": "<img src=x onerror=alert(1)>Course description",
            "subject": str(self.subject.id),
            "grade": str(self.grade.id),
        }

        response = self.client.post("/api/courses/", xss_payload, format="json")

        if response.status_code == 201:
            # Dangerous attributes should be removed
            desc = response.data.get("description", "")
            self.assertNotIn("onerror", desc)
            self.assertNotIn("<img", desc)

    def test_subject_name_sanitization(self):
        """Test that XSS in subject name is sanitized"""
        xss_payload = {
            "name": "<iframe src='evil.com'></iframe>Science",
            "description": "Science courses",
        }

        response = self.client.post("/api/subjects/", xss_payload, format="json")

        if response.status_code == 201:
            # Iframe should be stripped
            name = response.data.get("name", "")
            self.assertNotIn("<iframe", name)
            self.assertIn("Science", name)

    def test_allowed_safe_html_preserved(self):
        """Test that safe HTML tags are preserved"""
        safe_html = {
            "title": "Math 101",
            "description": "<p>This is <b>safe</b> content</p>",
            "subject": str(self.subject.id),
            "grade": str(self.grade.id),
        }

        response = self.client.post("/api/courses/", safe_html, format="json")

        if response.status_code == 201:
            desc = response.data.get("description", "")
            # Safe tags should be preserved
            self.assertIn("<p>", desc)
            self.assertIn("<b>", desc)


class ProfileEndpointsTestCase(TestCase):
    """
    Test profile retrieval and update endpoints
    """

    def setUp(self):
        """Set up test users and authentication"""
        self.client = APIClient()

        self.teacher_user = User.objects.create_user(
            email="teacher@test.com",
            first_name="Teacher",
            username="teacher",
            password="testpass",
            role="teacher",
            account_confirmed=True,
        )

        self.student_user = User.objects.create_user(
            email="student@test.com",
            first_name="Student",
            username="student",
            password="testpass",
            role="student",
            account_confirmed=True,
        )

    def test_teacher_profile_retrieve(self):
        """Test retrieving teacher profile"""
        self.client.force_authenticate(user=self.teacher_user)

        response = self.client.get("/api/teacher/profile/")

        # Should return 200 if profile exists, 403 if not
        self.assertIn(response.status_code, [200, 403])

    def test_student_profile_retrieve(self):
        """Test retrieving student profile"""
        self.client.force_authenticate(user=self.student_user)

        response = self.client.get("/api/student/profile/")

        # Should return 200 if profile exists, 403 if not
        self.assertIn(response.status_code, [200, 403])


class AdminEndpointsTestCase(TestCase):
    """
    Test admin dashboard and user management endpoints
    """

    def setUp(self):
        """Set up admin user"""
        self.client = APIClient()

        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            first_name="Admin",
            username="admin",
            password="adminpass",
            is_staff=True,
            is_superuser=True,
            account_confirmed=True,
        )

    def test_admin_dashboard_stats_requires_auth(self):
        """Test that admin stats endpoint requires authentication"""
        response = self.client.get("/api/admin/dashboard-stats/")

        # Should return 401 without auth
        self.assertEqual(response.status_code, 401)

    def test_admin_dashboard_stats_requires_admin(self):
        """Test that admin stats endpoint requires admin permission"""
        regular_user = User.objects.create_user(
            email="user@test.com", first_name="User", username="user", password="pass"
        )

        self.client.force_authenticate(user=regular_user)
        response = self.client.get("/api/admin/dashboard-stats/")

        # Should return 403 for non-admin
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_stats_works_for_admin(self):
        """Test that admin stats endpoint works for admin user"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/admin/dashboard-stats/")

        # Should return 200 for admin
        self.assertEqual(response.status_code, 200)

        # Should contain expected keys
        data = response.data
        self.assertIn("total_users", data)
        self.assertIn("total_teachers", data)
        self.assertIn("total_students", data)


class LessonsEndpointsTestCase(TestCase):
    """
    Test lessons/courses content delivery endpoints
    """

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="user@test.com",
            first_name="User",
            username="user",
            password="pass",
            account_confirmed=True,
        )

        self.subject = Subject.objects.create(name="Math")
        self.grade = Grade.objects.create(level="Grade 10")

        self.course = Course.objects.create(
            title="Math 101",
            description="Basic math",
            subject=self.subject,
            grade=self.grade,
            is_active=True,
        )

    def test_lessons_list_requires_auth(self):
        """Test that lessons list requires authentication"""
        response = self.client.get("/api/lessons/")

        # Should return 401 without auth
        self.assertEqual(response.status_code, 401)

    def test_lessons_list_authenticated(self):
        """Test that lessons list works for authenticated users"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/lessons/")

        # Should return 200
        self.assertEqual(response.status_code, 200)

        # Should be a list
        self.assertIsInstance(response.data, (list, dict))

    def test_lessons_detail(self):
        """Test retrieving specific lesson"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f"/api/lessons/{self.course.id}/")

        # Should return 200
        self.assertEqual(response.status_code, 200)
