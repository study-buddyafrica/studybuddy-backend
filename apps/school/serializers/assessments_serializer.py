from rest_framework import serializers

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


class QuestionSerializer(serializers.ModelSerializer):
    choices = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "order", "points", "choices"]


class AssessmentSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

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
