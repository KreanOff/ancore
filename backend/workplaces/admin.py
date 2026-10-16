from django.contrib import admin

from .models import SidebarFavorite, Workplace, WorkplaceMembership


class WorkplaceMembershipInline(admin.TabularInline):
    model = WorkplaceMembership
    extra = 0


@admin.register(Workplace)
class WorkplaceAdmin(admin.ModelAdmin):
    readonly_fields = ('code', 'slug', 'legacy_slug')
    list_display = ('name', 'code', 'owner', 'created_at')
    search_fields = ('name', 'code', 'description', 'owner__email', 'owner__username')
    inlines = [WorkplaceMembershipInline]


@admin.register(WorkplaceMembership)
class WorkplaceMembershipAdmin(admin.ModelAdmin):
    list_display = ('workplace', 'user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('workplace__name', 'user__email', 'user__username')


@admin.register(SidebarFavorite)
class SidebarFavoriteAdmin(admin.ModelAdmin):
    list_display = ('item_key', 'user', 'workplace', 'created_at')
    list_filter = ('item_key',)
    search_fields = ('item_key', 'workplace__name', 'user__email', 'user__username')
