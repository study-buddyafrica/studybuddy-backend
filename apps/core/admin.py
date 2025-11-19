# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import User, EmailVerificationCode

# class CustomUserAdmin(UserAdmin):
#     """Custom admin configuration for User model"""
    
#     list_display = (
#         'account_confirmed',
#         'email', 'first_name', 
#         'last_name', 'role',
#         'country', 
#         'is_staff', 'is_active', 
#         'created_at'
#     )
#     list_filter = (
#         'role', 'is_staff', 
#         'is_active', 'created_at',
#         'account_confirmed',
#         'country'
#     )
    
#     fieldsets = (
#         (None, {'fields': ('email', 'password')}),
#         ('Personal Info', 
#         {'fields': (
#             'first_name', 'last_name', 
#             'username','account_confirmed', 
#             'country'
#         )}),
#         ('Permissions', 
#         {'fields': (
#             'role', 'is_active', 
#             'is_staff', 'is_superuser', 
#             'groups', 'user_permissions'
#         )}),
#         ('Important Dates', 
#         {'fields': 
#         ('last_login', 'created_at', 
#           'updated_at'
#         )}),
#     )

#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'first_name', 'last_name', 'username', 'password1', 'password2', 'role', 'is_active', 'is_staff','account_confirmed', 'country')}
#         ),
#     )
    
#     search_fields = ('email', 'first_name', 'last_name', 'username')
#     ordering = ('-created_at',)
#     readonly_fields = ('created_at', 'updated_at', 'last_login')

# admin.site.register(User, CustomUserAdmin)
# admin.site.register(EmailVerificationCode)