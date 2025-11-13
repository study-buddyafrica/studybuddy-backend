from django.contrib import admin
from apps.school.models import (
    SessionBooking, Subject,
    Grade,Course, Subtopic,
    LiveSession,Topic
)

admin.site.register(SessionBooking)
admin.site.register(Grade)
admin.site.register(Course)
admin.site.register(Subject)
admin.site.register(Topic)
admin.site.register(Subtopic)
admin.site.register(LiveSession)
