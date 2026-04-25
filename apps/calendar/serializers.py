from rest_framework import serializers
from apps.calendar.models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "title",
            "start_datetime",
            "end_datetime",
            "event_type",
            "status",
            "reference_id",
        ]
        read_only_fields = fields
