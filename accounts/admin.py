from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Profil', {'fields': ('profile_photo', 'phone_number', 'job_title', 'bio', 'presence_status', 'last_seen_at')}),
    )
    list_display = ('email', 'username', 'first_name', 'last_name', 'job_title', 'presence_status', 'last_seen_at', 'is_staff', 'is_active')
    list_filter = UserAdmin.list_filter + ('presence_status',)
