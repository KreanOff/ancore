from django.contrib import admin

from .models import Company, CompanyMembership, Contact, ContactActivity, SharedItem, UserContact


class CompanyMembershipInline(admin.TabularInline):
    model = CompanyMembership
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'email', 'phone', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'phone', 'owner__email')
    inlines = [CompanyMembershipInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'company', 'company_record', 'email', 'phone', 'status', 'user', 'created_at')
    list_filter = ('status', 'created_at', 'last_contacted_at')
    search_fields = ('first_name', 'middle_name', 'last_name', 'company', 'company_record__name', 'email', 'phone')


@admin.register(UserContact)
class UserContactAdmin(admin.ModelAdmin):
    list_display = ('owner', 'target_user', 'linked_contact', 'created_at')
    search_fields = ('owner__email', 'target_user__email', 'target_user__first_name', 'target_user__middle_name', 'target_user__last_name')


@admin.register(ContactActivity)
class ContactActivityAdmin(admin.ModelAdmin):
    list_display = ('contact', 'actor', 'kind', 'action', 'created_at')
    list_filter = ('kind', 'action', 'created_at')
    search_fields = ('contact__first_name', 'contact__middle_name', 'contact__last_name', 'contact__company', 'message')


@admin.register(SharedItem)
class SharedItemAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'shared_by', 'shared_with', 'permission', 'created_at')
    list_filter = ('permission', 'created_at')
    search_fields = (
        'shared_by__email',
        'shared_by__first_name',
        'shared_by__middle_name',
        'shared_by__last_name',
        'shared_with__email',
        'shared_with__first_name',
        'shared_with__middle_name',
        'shared_with__last_name',
        'note',
    )
