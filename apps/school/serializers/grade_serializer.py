from rest_framework import serializers

from apps.school.models import Grade


class GradeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="level", read_only=True)

    class Meta:
        model = Grade
        fields = ["id", "level", "name"]
