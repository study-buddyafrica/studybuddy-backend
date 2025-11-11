from django.contrib import admin
from apps.school.models import SessionBooking, Grade,Subject, TeacherSubject, LiveSession

admin.site.register(SessionBooking)
admin.site.register(Grade)
admin.site.register(Subject)
admin.site.register(TeacherSubject)
admin.site.register(LiveSession)
