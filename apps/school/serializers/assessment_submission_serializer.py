"""Serializers for assessment submissions and grading."""

from __future__ import annotations

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.school.models import AssessmentSubmission, Assessment
from apps.core.serializers import SanitizeHTMLMixin


class AssessmentSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for reading assessment submissions."""

    assessment_title = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    is_late = serializers.BooleanField(read_only=True)
    max_score = serializers.SerializerMethodField()
    percentage_score = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentSubmission
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "course_title",
            "student",
            "student_name",
            "teacher_name",
            "submitted_at",
            "file_url",
            "answers",
            "grading",
            "feedback",
            "status",
            "is_late",
            "max_score",
            "percentage_score",
        ]
        read_only_fields = [
            "id",
            "submitted_at",
            "is_late",
        ]

    @extend_schema_field(serializers.CharField())
    def get_assessment_title(self, obj: AssessmentSubmission) -> str:
        return obj.assessment.title if obj.assessment else ""

    @extend_schema_field(serializers.CharField())
    def get_course_title(self, obj: AssessmentSubmission) -> str:
        if obj.assessment and obj.assessment.course:
            return obj.assessment.course.title
        return ""

    @extend_schema_field(serializers.CharField())
    def get_student_name(self, obj: AssessmentSubmission) -> str:
        if obj.student and obj.student.user:
            return f"{obj.student.user.first_name} {obj.student.user.last_name}".strip()
        return ""

    @extend_schema_field(serializers.CharField())
    def get_teacher_name(self, obj: AssessmentSubmission) -> str:
        if obj.assessment and obj.assessment.teacher and obj.assessment.teacher.user:
            teacher = obj.assessment.teacher
            return f"{teacher.user.first_name} {teacher.user.last_name}".strip()
        return ""

    @extend_schema_field(serializers.IntegerField())
    def get_max_score(self, obj: AssessmentSubmission) -> int:
        return obj.assessment.max_score if obj.assessment else 100

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_percentage_score(self, obj: AssessmentSubmission) -> float | None:
        if obj.grading is None or not obj.assessment:
            return None
        max_score = obj.assessment.max_score
        if max_score > 0:
            return round((obj.grading / max_score) * 100, 2)
        return None


class AssessmentSubmitSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    """Serializer for submitting an assessment."""

    sanitize_fields = []
    answers = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = AssessmentSubmission
        fields = ["answers", "file_url"]

    def validate(self, attrs):
        assessment = self.context.get("assessment")
        if not assessment:
            raise serializers.ValidationError("Assessment context is required.")

        assessment_type = assessment.assessment_type
        answers = attrs.get("answers")
        file_url = attrs.get("file_url")

        # Validate based on assessment type
        if assessment_type == "mcq":
            if not answers:
                raise serializers.ValidationError("MCQ assessments require answers.")
            self._validate_mcq_answers(assessment, answers)

        elif assessment_type == "file":
            if not file_url:
                raise serializers.ValidationError(
                    "File-upload assessments require a file URL."
                )
            if answers:
                raise serializers.ValidationError(
                    "File-upload assessments should not include answers."
                )

        elif assessment_type == "mixed":
            # Mixed can have both file and answers, but needs at least one
            if not answers and not file_url:
                raise serializers.ValidationError(
                    "Mixed assessments require at least answers or a file."
                )
            if answers:
                self._validate_mcq_answers(assessment, answers, partial=True)

        return attrs

    def _validate_mcq_answers(
        self, assessment: Assessment, answers: dict, partial: bool = False
    ):
        """Validate MCQ answers against assessment questions."""
        questions = {str(q.id): q for q in assessment.questions.all()}

        for question_id, choice_id in answers.items():
            if question_id not in questions:
                if not partial:
                    raise serializers.ValidationError(
                        f"Invalid question ID: {question_id}"
                    )
                continue

            # Validate choice exists for this question
            question = questions[question_id]
            valid_choices = set(str(c.id) for c in question.choices.all())

            if choice_id and choice_id not in valid_choices:
                raise serializers.ValidationError(
                    f"Invalid choice ID '{choice_id}' for question '{question_id}'"
                )

    def create(self, validated_data):
        assessment = self.context.get("assessment")
        student = self.context.get("student")

        return AssessmentSubmission.objects.create(
            assessment=assessment,
            student=student,
            answers=validated_data.get("answers"),
            file_url=validated_data.get("file_url"),
            status="pending",
        )


class AssessmentGradeSerializer(serializers.ModelSerializer):
    """Serializer for grading a submission."""

    class Meta:
        model = AssessmentSubmission
        fields = ["grading", "feedback"]

    def validate_grading(self, value):
        """Validate grading is within bounds."""
        if value is None:
            return value

        if value < 0:
            raise serializers.ValidationError("Grading cannot be negative.")

        # Max score validation happens in view where assessment is available
        return value

    def validate_feedback(self, value):
        """Sanitize feedback."""
        if value:
            # Limit feedback length
            max_length = 5000
            if len(value) > max_length:
                raise serializers.ValidationError(
                    f"Feedback cannot exceed {max_length} characters."
                )
        return value


class AssessmentDetailForStudentSerializer(serializers.ModelSerializer):
    """
    Detailed assessment info for students taking an assessment.
    Includes questions with choices but hides correct answers.
    """

    questions = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    time_remaining_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "description",
            "course_title",
            "teacher_name",
            "assessment_type",
            "due_date",
            "duration",
            "max_score",
            "questions",
            "time_remaining_minutes",
        ]

    @extend_schema_field(serializers.CharField())
    def get_course_title(self, obj: Assessment) -> str:
        return obj.course.title if obj.course else ""

    @extend_schema_field(serializers.CharField())
    def get_teacher_name(self, obj: Assessment) -> str:
        if obj.teacher and obj.teacher.user:
            return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}".strip()
        return ""

    @extend_schema_field(serializers.ListField())
    def get_questions(self, obj: Assessment):
        """Return questions without revealing correct answers."""
        questions = []
        for question in obj.questions.all().order_by("order"):
            choices = [
                {
                    "id": str(choice.id),
                    "text": choice.text,
                    # Note: is_correct is intentionally omitted
                }
                for choice in question.choices.all()
            ]
            questions.append(
                {
                    "id": str(question.id),
                    "text": question.text,
                    "order": question.order,
                    "points": question.points,
                    "choices": choices,
                }
            )
        return questions

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_time_remaining_minutes(self, obj: Assessment):
        """Calculate remaining time if due date is set."""
        if not obj.due_date:
            return None
        from django.utils import timezone

        now = timezone.now()
        if now > obj.due_date:
            return 0
        delta = obj.due_date - now
        return int(delta.total_seconds() / 60)


class AssessmentResultSerializer(serializers.ModelSerializer):
    """Serializer for showing assessment results to students after grading."""

    assessment_title = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    correct_answers = serializers.SerializerMethodField()
    percentage_score = serializers.SerializerMethodField()
    grade_letter = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentSubmission
        fields = [
            "id",
            "assessment_title",
            "course_title",
            "submitted_at",
            "grading",
            "feedback",
            "status",
            "percentage_score",
            "grade_letter",
            "correct_answers",
        ]

    @extend_schema_field(serializers.CharField())
    def get_assessment_title(self, obj: AssessmentSubmission) -> str:
        return obj.assessment.title if obj.assessment else ""

    @extend_schema_field(serializers.CharField())
    def get_course_title(self, obj: AssessmentSubmission) -> str:
        if obj.assessment and obj.assessment.course:
            return obj.assessment.course.title
        return ""

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_percentage_score(self, obj: AssessmentSubmission) -> float | None:
        if obj.grading is None or not obj.assessment:
            return None
        max_score = obj.assessment.max_score
        if max_score > 0:
            return round((obj.grading / max_score) * 100, 2)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_grade_letter(self, obj: AssessmentSubmission) -> str | None:
        """Convert percentage to letter grade."""
        percentage = self.get_percentage_score(obj)
        if percentage is None:
            return None

        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_correct_answers(self, obj: AssessmentSubmission):
        """Return correct answers for review (only for graded submissions)."""
        if obj.status != "graded" or not obj.assessment:
            return None

        # For MCQ, show correct answers
        if obj.assessment.assessment_type in ["mcq", "mixed"]:
            correct_answers = {}
            for question in obj.assessment.questions.all():
                correct_choice = question.choices.filter(is_correct=True).first()
                if correct_choice:
                    correct_answers[str(question.id)] = str(correct_choice.id)
            return correct_answers

        return None
