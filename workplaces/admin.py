from django.contrib import admin

from .models import Workplace, WorkplaceMembership


class WorkplaceMembershipInline(admin.TabularInline):
    model = WorkplaceMembership
    extra = 0


@admin.register(Workplace)
class WorkplaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    search_fields = ('name', 'owner__email', 'owner__username')
    inlines = [WorkplaceMembershipInline]


@admin.register(WorkplaceMembership)
class WorkplaceMembershipAdmin(admin.ModelAdmin):
    list_display = ('workplace', 'user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('workplace__name', 'user__email', 'user__username')
