"""HTML Sanitization for user-generated content"""

import bleach
from rest_framework import serializers


class SanitizeHTMLMixin:
    """
    Mixin for DRF serializers to sanitize HTML in specified fields.
    Removes malicious scripts and only allows safe HTML tags.

    Usage:
        class MySerializer(SanitizeHTMLMixin, serializers.ModelSerializer):
            sanitize_fields = ['description', 'bio']
            class Meta:
                model = MyModel
                fields = ['description', 'bio', ...]
    """

    sanitize_fields = []
    ALLOWED_TAGS = [
        "b",
        "i",
        "u",
        "p",
        "br",
        "strong",
        "em",
        "a",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
    ]
    ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}

    def validate(self, data):
        """Sanitize specified fields before validation"""
        for field_name in self.sanitize_fields:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = bleach.clean(
                    data[field_name],
                    tags=self.ALLOWED_TAGS,
                    attributes=self.ALLOWED_ATTRIBUTES,
                    strip=True,
                    strip_comments=True,
                )
        return super().validate(data)
