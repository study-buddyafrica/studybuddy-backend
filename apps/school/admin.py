from django.contrib import admin
from apps.school.models import (
    SessionBooking, Subject,Choice,
    Grade,Course, Subtopic,
    LiveSession,Topic, RevisionMaterial,
    Assessment,AssessmentSubmission,
)

admin.site.register(SessionBooking)
admin.site.register(Grade)
admin.site.register(Course)
admin.site.register(Choice)
admin.site.register(RevisionMaterial)
admin.site.register(Assessment)
admin.site.register(AssessmentSubmission)
admin.site.register(Subject)
admin.site.register(Topic)
admin.site.register(Subtopic)
admin.site.register(LiveSession)
