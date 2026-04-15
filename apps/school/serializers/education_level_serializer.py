from rest_framework import serializers

from apps.school.models import EducationLevel


class EducationLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationLevel
        fields = ["id", "code", "name", "description"]
