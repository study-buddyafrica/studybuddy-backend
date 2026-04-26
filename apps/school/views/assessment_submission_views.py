"""Assessment submission and grading views."""

from __future__ import annotations

from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.core.permissions import IsVerified, IsStudent, IsTeacherOrAdmin
from apps.core.auth.views.pagination_view import StandardResultsSetPagination
from apps.school.models import (
    Assessment,
    AssessmentSubmission,
    Choice,
    CourseEnrollment,
    EducationLevel,
)
from apps.school.serializers.assessment_submission_serializer import (
    AssessmentSubmissionSerializer,
    AssessmentSubmitSerializer,
    AssessmentGradeSerializer,
)


class CanAccessAssessment(permissions.BasePermission):
    """
    Permission to access assessments based on grade level.
    - Students can only access assessments at their grade level
    - Continuous Learning and University tracks bypass grade restrictions
    - Teachers and admins have full access
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff or hasattr(user, "teacher_profile"):
            return True
        return True  # Students can attempt, object-level check handles gating

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or hasattr(user, "teacher_profile"):
            return True

        if hasattr(user, "student_profile"):
            student = user.student_profile
            assessment = obj if isinstance(obj, Assessment) else obj.assessment

            # Check if student is enrolled in the course
            if not CourseEnrollment.objects.filter(
                student=student, course=assessment.course, is_active=True
            ).exists():
                return False

            # Check for bypass: Continuous Learning and University tracks
            if self._has_education_track_bypass(student, assessment):
                return True

            # Grade-level gating: student must have matching grade
            return self._check_grade_access(student, assessment)

        return False

    @staticmethod
    def _has_education_track_bypass(student, assessment) -> bool:
        """
        Check if student qualifies for bypass based on education track.
        Continuous Learning and University tracks bypass grade restrictions.
        """
        if not student.education_level:
            return False

        bypass_codes = [
            EducationLevel.AudienceTier.CONTINUOUS,
            EducationLevel.AudienceTier.UNIVERSITY,
        ]

        # Student's education level allows bypass
        if student.education_level.code in bypass_codes:
            return True

        # Assessment's education level allows bypass
        if assessment.course and assessment.course.education_level:
            if assessment.course.education_level.code in bypass_codes:
                return True

        return False

    @staticmethod
    def _check_grade_access(student, assessment) -> bool:
        """Check if student's grade allows access to assessment."""
        student_grade = student.grade
        assessment_grade = assessment.course.grade if assessment.course else None

        if not student_grade or not assessment_grade:
            # If either grade is not set, allow access (lenient default)
            return True

        return student_grade.id == assessment_grade.id


class AssessmentAccessCheckView(generics.GenericAPIView):
    """
    GET /api/assessments/<uuid:assessment_id>/access-check/
    Check if student can access an assessment (grade-level gating check).
    Returns access status and bypass information.
    """

    permission_classes = [permissions.IsAuthenticated, IsVerified, IsStudent]

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        parameters=[
            OpenApiParameter("assessment_id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
    )
    def get(self, request, assessment_id):
        user = request.user
        student = user.student_profile

        try:
            assessment = Assessment.objects.select_related(
                "course", "course__grade", "course__education_level"
            ).get(id=assessment_id)
        except Assessment.DoesNotExist:
            return Response(
                {"detail": "Assessment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check enrollment
        is_enrolled = CourseEnrollment.objects.filter(
            student=student, course=assessment.course, is_active=True
        ).exists()

        if not is_enrolled:
            return Response(
                {
                    "can_access": False,
                    "reason": "not_enrolled",
                    "message": "You must be enrolled in this course to access the assessment.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check for previous submission
        existing_submission = AssessmentSubmission.objects.filter(
            assessment=assessment, student=student
        ).first()

        if existing_submission:
            return Response(
                {
                    "can_access": False,
                    "reason": "already_submitted",
                    "message": "You have already submitted this assessment.",
                    "submission_id": str(existing_submission.id),
                    "status": existing_submission.status,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check bypass
        bypass_codes = [
            EducationLevel.AudienceTier.CONTINUOUS,
            EducationLevel.AudienceTier.UNIVERSITY,
        ]

        has_bypass = False
        bypass_reason = None

        if student.education_level and student.education_level.code in bypass_codes:
            has_bypass = True
            bypass_reason = f"Your {student.education_level.name} track allows access to all grade levels."
        elif (
            assessment.course
            and assessment.course.education_level
            and assessment.course.education_level.code in bypass_codes
        ):
            has_bypass = True
            bypass_reason = f"This {assessment.course.education_level.name} course allows access regardless of grade level."

        # Check grade match
        student_grade = student.grade
        assessment_grade = assessment.course.grade if assessment.course else None

        grade_match = False
        if not student_grade or not assessment_grade:
            grade_match = True  # Lenient default
        else:
            grade_match = student_grade.id == assessment_grade.id

        if has_bypass or grade_match:
            return Response(
                {
                    "can_access": True,
                    "bypass_applied": has_bypass,
                    "bypass_reason": bypass_reason,
                    "student_grade": student_grade.level if student_grade else None,
                    "assessment_grade": assessment_grade.level
                    if assessment_grade
                    else None,
                    "assessment": {
                        "id": str(assessment.id),
                        "title": assessment.title,
                        "assessment_type": assessment.assessment_type,
                        "max_score": assessment.max_score,
                        "due_date": assessment.due_date,
                        "duration": assessment.duration.isoformat()
                        if assessment.duration
                        else None,
                    },
                }
            )

        return Response(
            {
                "can_access": False,
                "reason": "grade_mismatch",
                "message": f"This assessment is for {assessment_grade.level if assessment_grade else 'a different grade'}. Your grade is {student_grade.level if student_grade else 'not set'}.",
                "student_grade": student_grade.level if student_grade else None,
                "assessment_grade": assessment_grade.level
                if assessment_grade
                else None,
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class AssessmentSubmitView(generics.CreateAPIView):
    """
    POST /api/assessments/<uuid:assessment_id>/submit/
    Student submits an assessment.
    Validates grade-level access and prevents duplicate submissions.
    """

    serializer_class = AssessmentSubmitSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsVerified,
        IsStudent,
        CanAccessAssessment,
    ]

    @extend_schema(
        responses={201: AssessmentSubmissionSerializer},
        parameters=[
            OpenApiParameter("assessment_id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
    )
    def post(self, request, assessment_id):
        user = request.user
        student = user.student_profile

        try:
            assessment = (
                Assessment.objects.select_related(
                    "course", "course__grade", "course__education_level"
                )
                .prefetch_related("questions", "questions__choices")
                .get(id=assessment_id)
            )
        except Assessment.DoesNotExist:
            return Response(
                {"detail": "Assessment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check permission using CanAccessAssessment
        permission = CanAccessAssessment()
        if not permission.has_object_permission(request, self, assessment):
            return Response(
                {"detail": "You do not have permission to access this assessment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check for existing submission
        if AssessmentSubmission.objects.filter(
            assessment=assessment, student=student
        ).exists():
            return Response(
                {"detail": "You have already submitted this assessment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            submission = serializer.save(assessment=assessment, student=student)

            # Auto-grade if MCQ or Mixed
            if assessment.assessment_type in ["mcq", "mixed"]:
                self._auto_grade(submission, assessment)

        return Response(
            AssessmentSubmissionSerializer(
                submission, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    def _auto_grade(self, submission: AssessmentSubmission, assessment: Assessment):
        """Auto-grade MCQ submissions."""
        answers = submission.answers or {}
        total_points = 0
        earned_points = 0

        for question in assessment.questions.all():
            total_points += question.points
            question_id = str(question.id)
            selected_choice_id = answers.get(question_id)

            if selected_choice_id:
                try:
                    selected_choice = Choice.objects.get(id=selected_choice_id)
                    if selected_choice.is_correct:
                        earned_points += question.points
                except Choice.DoesNotExist:
                    pass

        if total_points > 0:
            # Calculate percentage and scale to max_score
            percentage = earned_points / total_points
            grading = round(percentage * assessment.max_score, 2)
        else:
            grading = 0

        submission.grading = grading
        submission.status = "graded"
        submission.save(update_fields=["grading", "status"])


class AssessmentSubmissionListView(generics.ListAPIView):
    """
    GET /api/assessment-submissions/
    - Students: see their own submissions
    - Teachers: see submissions for their assessments
    - Admins: see all submissions
    """

    serializer_class = AssessmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return AssessmentSubmission.objects.all()

        if hasattr(user, "teacher_profile"):
            return AssessmentSubmission.objects.filter(
                assessment__teacher=user.teacher_profile
            ).select_related("student__user", "assessment__course")

        if hasattr(user, "student_profile"):
            return AssessmentSubmission.objects.filter(
                student=user.student_profile
            ).select_related("assessment__course", "assessment__teacher__user")

        return AssessmentSubmission.objects.none()


class AssessmentSubmissionDetailView(generics.RetrieveAPIView):
    """
    GET /api/assessment-submissions/<uuid:id>/
    Retrieve a specific submission with details.
    """

    serializer_class = AssessmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return AssessmentSubmission.objects.all()

        if hasattr(user, "teacher_profile"):
            return AssessmentSubmission.objects.filter(
                assessment__teacher=user.teacher_profile
            )

        if hasattr(user, "student_profile"):
            return AssessmentSubmission.objects.filter(student=user.student_profile)

        return AssessmentSubmission.objects.none()


class AssessmentGradeView(generics.UpdateAPIView):
    """
    PATCH /api/assessment-submissions/<uuid:id>/grade/
    Teachers grade a submission (for file-upload or manual grading).
    """

    serializer_class = AssessmentGradeSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsVerified,
        IsTeacherOrAdmin,
    ]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return AssessmentSubmission.objects.all()

        if hasattr(user, "teacher_profile"):
            return AssessmentSubmission.objects.filter(
                assessment__teacher=user.teacher_profile
            )

        return AssessmentSubmission.objects.none()

    @extend_schema(
        responses={200: AssessmentSubmissionSerializer},
        parameters=[
            OpenApiParameter("id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
    )
    def patch(self, request, *args, **kwargs):
        submission = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Validate grading constraints
        grading = serializer.validated_data.get("grading")
        if grading is not None:
            if grading < 0 or grading > submission.assessment.max_score:
                return Response(
                    {
                        "detail": f"Grading must be between 0 and {submission.assessment.max_score}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            submission.grading = serializer.validated_data.get(
                "grading", submission.grading
            )
            submission.feedback = serializer.validated_data.get(
                "feedback", submission.feedback
            )
            submission.status = "graded"
            submission.save(update_fields=["grading", "feedback", "status"])

        return Response(
            AssessmentSubmissionSerializer(
                submission, context={"request": request}
            ).data,
            status=status.HTTP_200_OK,
        )


class StudentAssessmentListView(generics.ListAPIView):
    """
    GET /api/student/available-assessments/
    List assessments available to the logged-in student.
    Applies grade-level gating with bypass for Continuous/University tracks.
    """

    serializer_class = AssessmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified, IsStudent]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Assessment.objects.none()  # Placeholder, overridden in list()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def list(self, request, *args, **kwargs):
        user = request.user
        student = user.student_profile

        # Get enrolled courses
        enrolled_courses = CourseEnrollment.objects.filter(
            student=student, is_active=True
        ).values_list("course_id", flat=True)

        # Get assessments for enrolled courses
        assessments = Assessment.objects.filter(
            course_id__in=enrolled_courses
        ).select_related("course", "course__grade", "course__education_level")

        # Get existing submissions
        submitted_ids = set(
            AssessmentSubmission.objects.filter(student=student).values_list(
                "assessment_id", flat=True
            )
        )

        available_assessments = []

        for assessment in assessments:
            # Skip if already submitted
            if assessment.id in submitted_ids:
                continue

            # Check access
            can_access = self._can_access_assessment(student, assessment)

            assessment_data = {
                "id": str(assessment.id),
                "title": assessment.title,
                "description": assessment.description,
                "course": assessment.course.title if assessment.course else None,
                "assessment_type": assessment.assessment_type,
                "max_score": assessment.max_score,
                "due_date": assessment.due_date,
                "duration": assessment.duration.isoformat()
                if assessment.duration
                else None,
                "can_access": can_access["can_access"],
                "access_reason": can_access["reason"],
                "bypass_applied": can_access["bypass"],
            }
            available_assessments.append(assessment_data)

        return Response(
            {
                "count": len(available_assessments),
                "results": available_assessments,
            }
        )

    def _can_access_assessment(self, student, assessment):
        """Check if student can access assessment."""
        # Check bypass
        bypass_codes = [
            EducationLevel.AudienceTier.CONTINUOUS,
            EducationLevel.AudienceTier.UNIVERSITY,
        ]

        if student.education_level and student.education_level.code in bypass_codes:
            return {
                "can_access": True,
                "reason": f"{student.education_level.name} track bypass",
                "bypass": True,
            }

        if (
            assessment.course
            and assessment.course.education_level
            and assessment.course.education_level.code in bypass_codes
        ):
            return {
                "can_access": True,
                "reason": f"{assessment.course.education_level.name} course bypass",
                "bypass": True,
            }

        # Check grade match
        student_grade = student.grade
        assessment_grade = assessment.course.grade if assessment.course else None

        if not student_grade or not assessment_grade:
            return {
                "can_access": True,
                "reason": "Grade not set - access allowed",
                "bypass": False,
            }

        if student_grade.id == assessment_grade.id:
            return {
                "can_access": True,
                "reason": "Grade level matches",
                "bypass": False,
            }

        return {
            "can_access": False,
            "reason": f"Grade mismatch: Your grade ({student_grade.level}) vs Assessment grade ({assessment_grade.level})",
            "bypass": False,
        }
