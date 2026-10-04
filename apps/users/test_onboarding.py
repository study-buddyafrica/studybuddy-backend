import io
import uuid
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from apps.core.models import User, OnboardingStep
from apps.core.validators import validate_kyc_document
from apps.core.auth.serializers.auth_serializer import CustomTokenObtainPairSerializer
from apps.school.models import EducationLevel, Grade, School
from apps.users.models import (
    StudentProfile,
    TeacherProfile,
    ParentProfile,
    ParentChild,
)
from apps.transactions.models import Wallet


class KYCDocumentValidationTests(APITestCase):
    def test_valid_pdf_file_passes(self):
        pdf_content = b"%PDF-1.4 simulated pdf document stream"
        uploaded = SimpleUploadedFile("id_card.pdf", pdf_content, content_type="application/pdf")
        validated = validate_kyc_document(uploaded)
        self.assertEqual(validated, uploaded)

    def test_valid_jpeg_file_passes(self):
        jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF simulated jpeg image"
        uploaded = SimpleUploadedFile("scan.jpg", jpeg_content, content_type="image/jpeg")
        validated = validate_kyc_document(uploaded)
        self.assertEqual(validated, uploaded)

    def test_valid_png_file_passes(self):
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00 simulated png image"
        uploaded = SimpleUploadedFile("scan.png", png_content, content_type="image/png")
        validated = validate_kyc_document(uploaded)
        self.assertEqual(validated, uploaded)

    def test_oversized_file_rejected(self):
        # 5MB + 1 byte
        huge_content = b"%PDF" + b"0" * (5 * 1024 * 1024 + 1)
        uploaded = SimpleUploadedFile("big.pdf", huge_content, content_type="application/pdf")
        with self.assertRaises(DjangoValidationError) as ctx:
            validate_kyc_document(uploaded)
        self.assertIn("exceeds maximum allowed limit", str(ctx.exception))

    def test_invalid_magic_bytes_rejected(self):
        bad_content = b"MZ\x90\x00ThisIsAnExecutable"
        uploaded = SimpleUploadedFile("malware.exe", bad_content, content_type="application/octet-stream")
        with self.assertRaises(DjangoValidationError) as ctx:
            validate_kyc_document(uploaded)
        self.assertIn("Only PDF, JPG, and PNG", str(ctx.exception))


class JWTClaimsAndAuthSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="token_test@studybuddy.africa",
            username="token_tester",
            first_name="Token",
            last_name="Tester",
            role="student",
            password="SecurePassword123!",
            onboarding_step=OnboardingStep.STEP_2_PROFILE,
        )

    def test_custom_token_contains_onboarding_claims(self):
        token = CustomTokenObtainPairSerializer.get_token(self.user)
        self.assertEqual(token["onboarding_step"], "step_2_profile")
        self.assertFalse(token["is_onboarded"])
        self.assertEqual(token["role"], "student")

    def test_login_endpoint_returns_onboarding_step(self):
        response = self.client.post(
            "/api/login/",
            {
                "email": "token_test@studybuddy.africa",
                "password": "SecurePassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data.get("onboarding_step"), "step_2_profile")
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["onboarding_step"], "step_2_profile")
        self.assertFalse(response.data["user"]["is_onboarded"])


class OnboardingStateEngineEndpointsTests(APITestCase):
    def setUp(self):
        self.k12, _ = EducationLevel.objects.get_or_create(
            code=EducationLevel.AudienceTier.K12,
            defaults={"name": "K-12", "description": "Primary & Secondary"},
        )
        self.grade, _ = Grade.objects.get_or_create(
            level=Grade.GradeLevel.GRADE_8,
        )

        # 1. Student User in pending_otp
        self.student_user = User.objects.create_user(
            email="student@studybuddy.africa",
            username="student_step_test",
            first_name="Amara",
            last_name="Kamau",
            role="student",
            password="SecurePassword123!",
            onboarding_step=OnboardingStep.PENDING_OTP,
        )

        # 2. Teacher User in step_2_profile
        self.teacher_user = User.objects.create_user(
            email="teacher@studybuddy.africa",
            username="teacher_step_test",
            first_name="John",
            last_name="Mwangi",
            role="teacher",
            password="SecurePassword123!",
            onboarding_step=OnboardingStep.STEP_2_PROFILE,
        )
        TeacherProfile.objects.create(user=self.teacher_user, hourly_rate=Decimal("1000.00"))

        # 3. Parent User in step_2_profile
        self.parent_user = User.objects.create_user(
            email="parent@studybuddy.africa",
            username="parent_step_test",
            first_name="Grace",
            last_name="Wanjiku",
            role="parent",
            password="SecurePassword123!",
            onboarding_step=OnboardingStep.STEP_2_PROFILE,
        )
        ParentProfile.objects.create(user=self.parent_user)

    def test_status_endpoint_returns_correct_hydration_data(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/v1/onboarding/status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        data = response.data["data"]
        self.assertEqual(data["onboarding_step"], "pending_otp")
        self.assertEqual(data["step_number"], 1)
        self.assertFalse(data["is_completed"])
        self.assertEqual(data["resume_route"], "/onboarding/student?step=1")

    def test_step_2_blocked_if_user_in_pending_otp(self):
        self.client.force_authenticate(user=self.student_user)
        payload = {
            "curriculum_type": "CBC",
            "grade_id": str(self.grade.id),
        }
        response = self.client.patch("/api/v1/onboarding/step-2/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Handle either standard DRF {"detail": "..."} or drf_standardized_errors format
        error_msg = ""
        if "detail" in response.data:
            error_msg = response.data["detail"]
        elif "errors" in response.data:
            error_msg = response.data["errors"][0].get("detail", "")
        self.assertIn("Please complete step 1", error_msg)

    def test_student_step_2_and_step_3_and_complete_progression(self):
        # Move student to step_2_profile
        self.student_user.onboarding_step = OnboardingStep.STEP_2_PROFILE
        self.student_user.save()
        self.client.force_authenticate(user=self.student_user)

        # 1. Submit Step 2
        step2_payload = {
            "curriculum_type": "CBC",
            "education_level_id": str(self.k12.id),
            "grade_id": str(self.grade.id),
            "school_name": "Nairobi Junior Academy",
            "gender": "Female",
        }
        step2_res = self.client.patch("/api/v1/onboarding/step-2/", step2_payload, format="json")
        self.assertEqual(step2_res.status_code, status.HTTP_200_OK)
        self.assertEqual(step2_res.data["data"]["onboarding_step"], "step_3_academic_kyc")
        self.assertEqual(step2_res.data["data"]["next_step"], 3)

        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.onboarding_step, OnboardingStep.STEP_3_ACADEMIC_KYC)
        self.assertEqual(self.student_user.student_profile.curriculum_type, "CBC")
        self.assertEqual(self.student_user.student_profile.school.name, "Nairobi Junior Academy")

        # 2. Submit Step 3
        step3_payload = {
            "target_subjects": ["Mathematics", "Integrated Science"],
            "primary_learning_goal": "Excel in Grade 8 CBC Assessments",
            "parent_phone_number": "+254712345678",
        }
        step3_res = self.client.patch("/api/v1/onboarding/step-3/", step3_payload, format="json")
        self.assertEqual(step3_res.status_code, status.HTTP_200_OK)
        self.assertEqual(step3_res.data["data"]["onboarding_step"], "step_4_launch")
        self.assertEqual(step3_res.data["data"]["next_step"], 4)

        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.onboarding_step, OnboardingStep.STEP_4_LAUNCH)
        self.assertEqual(self.student_user.student_profile.target_subjects, ["Mathematics", "Integrated Science"])
        self.assertEqual(self.student_user.student_profile.parent_phone_number, "+254712345678")

        # 3. Complete Onboarding
        complete_res = self.client.post("/api/v1/onboarding/complete/", {}, format="json")
        self.assertEqual(complete_res.status_code, status.HTTP_200_OK)
        self.assertEqual(complete_res.data["data"]["onboarding_step"], "completed")
        self.assertEqual(complete_res.data["data"]["dashboard_url"], "/student-dashboard/home")
        self.assertTrue(complete_res.data["data"]["user"]["is_onboarded"])
        self.assertIn("access", complete_res.data["tokens"])

        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.onboarding_step, OnboardingStep.COMPLETED)
        self.assertTrue(self.student_user.account_confirmed)
        # Check wallet auto-provisioned
        wallet = Wallet.objects.filter(user=self.student_user).first()
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.account_type, "student")

    def test_teacher_step_2_and_step_3_progression(self):
        self.client.force_authenticate(user=self.teacher_user)

        # Step 2: KYC Identity
        pdf_file = SimpleUploadedFile("national_id.pdf", b"%PDF-1.4 simulated id card", content_type="application/pdf")
        step2_payload = {
            "national_identity_number": "29847192",
            "tsc_number": "TSC/849201",
            "experience": 7,
            "national_identity_card": pdf_file,
            "bio": "Certified STEM educator.",
        }
        step2_res = self.client.patch("/api/v1/onboarding/step-2/", step2_payload, format="multipart")
        self.assertEqual(step2_res.status_code, status.HTTP_200_OK)
        self.assertEqual(step2_res.data["data"]["onboarding_step"], "step_3_academic_kyc")

        self.teacher_user.refresh_from_db()
        self.assertEqual(self.teacher_user.teacher_profile.national_identity_number, "29847192")
        self.assertEqual(self.teacher_user.teacher_profile.tsc_number, "TSC/849201")
        self.assertEqual(self.teacher_user.teacher_profile.experience, 7)

        # Step 3: Academic Qualifications & Rate
        cert_file = SimpleUploadedFile("degree.pdf", b"%PDF-1.4 simulated degree", content_type="application/pdf")
        step3_payload = {
            "highest_qualification": "Bachelor of Education (B.Ed)",
            "institution_attended": "Kenyatta University",
            "curriculums_taught": ["CBC", "8_4_4"],
            "hourly_rate_kes": "1500.00",
            "academic_certificate": cert_file,
        }
        step3_res = self.client.patch("/api/v1/onboarding/step-3/", step3_payload, format="multipart")
        self.assertEqual(step3_res.status_code, status.HTTP_200_OK)
        self.assertEqual(step3_res.data["data"]["onboarding_step"], "step_4_launch")

        self.teacher_user.refresh_from_db()
        self.assertEqual(self.teacher_user.teacher_profile.highest_qualification, "Bachelor of Education (B.Ed)")
        self.assertEqual(self.teacher_user.teacher_profile.curriculums_taught, ["CBC", "8_4_4"])
        self.assertEqual(float(self.teacher_user.teacher_profile.hourly_rate.amount), 1500.00)
        self.assertEqual(self.teacher_user.teacher_profile.verification_status, "ongoing")
        self.assertFalse(self.teacher_user.teacher_profile.is_verified)

    def test_parent_step_2_ward_association_and_step_3_billing(self):
        # Create student profile to link
        student = StudentProfile.objects.create(
            user=self.student_user,
            grade=self.grade,
            parent_phone_number="+254700000000",
        )

        self.client.force_authenticate(user=self.parent_user)

        # Step 2: Relationship & child linking by student email
        step2_payload = {
            "relationship_type": "Mother",
            "child_identifier": self.student_user.email,
        }
        step2_res = self.client.patch("/api/v1/onboarding/step-2/", step2_payload, format="json")
        self.assertEqual(step2_res.status_code, status.HTTP_200_OK)
        self.assertEqual(step2_res.data["data"]["onboarding_step"], "step_3_academic_kyc")

        self.parent_user.refresh_from_db()
        self.assertEqual(self.parent_user.parent_profile.relationship_type, "Mother")
        # Verify ParentChild link created
        link = ParentChild.objects.filter(parent=self.parent_user.parent_profile, child=student).first()
        self.assertIsNotNone(link)
        self.assertEqual(link.status, "active")

        # Step 3: M-Pesa billing phone & spend limit
        step3_payload = {
            "mpesa_billing_phone": "+254722123456",
            "weekly_spend_limit_kes": "7500.00",
            "notification_preferences": {"sms_attendance": True, "weekly_report": True},
        }
        step3_res = self.client.patch("/api/v1/onboarding/step-3/", step3_payload, format="json")
        self.assertEqual(step3_res.status_code, status.HTTP_200_OK)
        self.assertEqual(step3_res.data["data"]["onboarding_step"], "step_4_launch")

        self.parent_user.refresh_from_db()
        self.assertEqual(self.parent_user.parent_profile.mpesa_billing_phone, "+254722123456")
        self.assertEqual(float(self.parent_user.parent_profile.weekly_spend_limit_kes), 7500.00)
        self.assertTrue(self.parent_user.parent_profile.notification_preferences["sms_attendance"])
