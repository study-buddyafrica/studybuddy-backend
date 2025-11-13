from rest_framework import serializers

from apps.school.models import AssessmentType
from apps.school.models import (
    RevisionMaterial, 
    Assessment, Question, 
    Choice
)

class RevisionMaterialSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = RevisionMaterial
        fields = ["id", "title", "description", "file", "file_url", "course"]
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def validate_course(self, value):
        user = self.context["request"].user
        if hasattr(user, "teacher_profile") and not user.is_staff:
            if value.teacher != user.teacher_profile:
                raise serializers.ValidationError(
                    "You cannot add materials to a course you don't own."
                )
        return value


class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]

class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ["id", "text", "order", "points", "choices"]

class AssessmentSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "description",
            "course",
            "assessment_type",
            "due_date",
            "max_score",
            "questions",
        ]

    def validate_course(self, value):
        user = self.context["request"].user
        if hasattr(user, "teacher_profile") and not user.is_staff:
            if value.teacher != user.teacher_profile:
                raise serializers.ValidationError(
                    "You cannot add assessments to a course you don't own."
                )
        return value

    def validate(self, attrs):
        assessment_type = attrs.get("assessment_type")
        questions = attrs.get("questions", [])

        if assessment_type in [AssessmentType.MCQ, AssessmentType.MIXED] and not questions:
            raise serializers.ValidationError("At least one question is required for MCQ or Mixed assessments.")

        if assessment_type == AssessmentType.FILE and questions:
            raise serializers.ValidationError("File-upload assessments should not have questions.")

        if assessment_type == AssessmentType.MIXED:
            for q in questions:
                if "choices" not in q or not q["choices"]:
                    raise serializers.ValidationError("All MCQs in Mixed assessments must have choices.")

        return attrs

    def create(self, validated_data):
        questions_data = validated_data.pop("questions", [])
        assessment = Assessment.objects.create(**validated_data)

        for q_data in questions_data:
            choices_data = q_data.pop("choices", [])
            question = Question.objects.create(assessment=assessment, **q_data)
            for c_data in choices_data:
                Choice.objects.create(question=question, **c_data)

        return assessment

    def update(self, instance, validated_data):
        questions_data = validated_data.pop("questions", [])
        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.course = validated_data.get("course", instance.course)
        instance.assessment_type = validated_data.get("assessment_type", instance.assessment_type)
        instance.due_date = validated_data.get("due_date", instance.due_date)
        instance.max_score = validated_data.get("max_score", instance.max_score)
        instance.save()

        existing_questions = {str(q.id): q for q in instance.questions.all()}

        for q_data in questions_data:
            q_id = str(q_data.get("id")) if q_data.get("id") else None
            choices_data = q_data.pop("choices", [])

            if q_id and q_id in existing_questions:
                question = existing_questions[q_id]
                question.text = q_data.get("text", question.text)
                question.order = q_data.get("order", question.order)
                question.points = q_data.get("points", question.points)
                question.save()

                existing_choices = {str(c.id): c for c in question.choices.all()}
                for c_data in choices_data:
                    c_id = str(c_data.get("id")) if c_data.get("id") else None
                    if c_id and c_id in existing_choices:
                        choice = existing_choices[c_id]
                        choice.text = c_data.get("text", choice.text)
                        choice.is_correct = c_data.get("is_correct", choice.is_correct)
                        choice.save()
                    else:
                        Choice.objects.create(question=question, **c_data)

            else:
        
                question = Question.objects.create(assessment=instance, **q_data)
                for c_data in choices_data:
                    Choice.objects.create(question=question, **c_data)

        return instance