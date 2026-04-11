from rest_framework import serializers

from apps.school.models import Subject
from apps.core.serializers import SanitizeHTMLMixin


class SubjectSerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
    sanitize_fields = ["name", "description"]

    class Meta:
        model = Subject
        fields = ["id", "name", "description"]
