from django.contrib import admin
from .models import (
    ParentProfile, TeacherProfile, StudentProfile, 
    ParentChild, Availability, TeacherRating
)

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_email')
    list_filter = ('user__is_active',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('get_children',)
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    
    def get_children_count(self, obj):
        return obj.children.count()
    get_children_count.short_description = 'Children Count'
    
    def get_children(self, obj):
        return ", ".join([str(child) for child in obj.children.all()])
    get_children.short_description = 'Children'


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_email', 'tsc_number', 'hourly_rate', "is_verified",'tsc_number_certificate','experience')
    list_filter = ('user__is_active',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'tsc_number')
    readonly_fields = ('get_email', 'get_subjects')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'get_email','id_number','gender','birth_date','profile_picture')
        }),
        ('Professional Information', {
            'fields': ('tsc_number', 'academic_certificate', 'bio', 'phone', 'hourly_rate',"is_verified",'tsc_number_certificate','experience','grade', 'subjects')
        }),
    
    )
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    
    def get_subjects_count(self, obj):
        return obj.subjects.count()
    get_subjects_count.short_description = 'Subjects Count'
    
    def get_subjects(self, obj):
        return ", ".join([subject.name for subject in obj.subjects.all()])
    get_subjects.short_description = 'Subjects'


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_email', 'grade', 'school', 'enrollment_date')
    list_filter = ('grade', 'school', 'enrollment_date')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'contact_name')
    readonly_fields = ('get_email', 'get_parents', 'get_subjects', 'enrollment_date')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'get_email')
        }),
        ('Academic Information', {
            'fields': ('grade', 'school', 'enrollment_date')
        }),
        ('Contact Information', {
            'fields': ('contact_name', 'guardian_contact')
        }),
    )
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    
    def get_parents_count(self, obj):
        return obj.parents.count()
    get_parents_count.short_description = 'Parents Count'
    
    def get_parents(self, obj):
        return ", ".join([str(parent) for parent in obj.parents.all()])
    get_parents.short_description = 'Parents'
    
    def get_subjects_count(self, obj):
        return obj.subjects.count()
    get_subjects_count.short_description = 'Subjects Count'
    
    def get_subjects(self, obj):
        return ", ".join([subject.name for subject in obj.subjects.all()])
    get_subjects.short_description = 'Subjects'


@admin.register(ParentChild)
class ParentChildAdmin(admin.ModelAdmin):
    list_display = ('parent', 'child')
    search_fields = (
        'parent__user__email', 
        'parent__user__first_name', 
        'child__user__email', 
        'child__user__first_name'
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'parent__user', 'child__user'
        )


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'date', 'end_date', 'is_blocked')
    list_filter = ('is_blocked', 'date', 'teacher')
    search_fields = (
        'teacher__user__email', 
        'teacher__user__first_name',
        'teacher__user__last_name'
    )
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__user')


@admin.register(TeacherRating)
class TeacherRatingAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'student', 'rating')
    list_filter = ('rating', 'teacher')
    search_fields = (
        'teacher__user__email',
        'teacher__user__first_name',
        'student__user__email', 
        'student__user__first_name'
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'teacher__user', 'student__user'
        )