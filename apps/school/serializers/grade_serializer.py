from rest_framework import serializers

from apps.school.models import Grade


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ["id", "level"]
