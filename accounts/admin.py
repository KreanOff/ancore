from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Status obecności', {'fields': ('presence_status',)}),
    )
    list_display = ('email', 'first_name', 'last_name', 'presence_status', 'is_staff', 'is_active')
    list_filter = UserAdmin.list_filter + ('presence_status',)
