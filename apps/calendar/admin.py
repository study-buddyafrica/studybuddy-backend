from django.contrib import admin
from apps.calendar.models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ["title", "event_type", "status", "start_datetime", "end_datetime"]
    list_filter = ["event_type", "status"]
    search_fields = ["title"]
    ordering = ["start_datetime"]
