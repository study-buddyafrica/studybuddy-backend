from django.contrib import admin
from apps.school.models import (
    SessionBooking, Subject,
    Grade,Course, 
    LiveSession
)

admin.site.register(SessionBooking)
admin.site.register(Grade)
admin.site.register(Course)
admin.site.register(Subject)
admin.site.register(LiveSession)
