from django.contrib import admin
from .models import Task, TaskAttachment, TaskProject, TaskProjectFieldOption, TaskSection, TaskTag

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'title', 'section', 'user', 'status', 'priority', 'due_at', 'created_at')
    list_filter = ('status', 'priority', 'due_at', 'created_at')
    search_fields = ('title', 'description')
    inlines = [TaskAttachmentInline]


class TaskSectionInline(admin.TabularInline):
    model = TaskSection
    extra = 1


@admin.register(TaskProject)
class TaskProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority', 'due_at', 'company', 'user', 'created_at')
    list_filter = ('priority', 'due_at', 'created_at')
    search_fields = ('name', 'code', 'company__name')
    inlines = [TaskSectionInline]


@admin.register(TaskProjectFieldOption)
class TaskProjectFieldOptionAdmin(admin.ModelAdmin):
    list_display = ('label', 'field_type', 'color', 'owner', 'workplace', 'is_active', 'position')
    list_filter = ('field_type', 'is_active', 'workplace')
    search_fields = ('label', 'owner__username', 'owner__email')


@admin.register(TaskSection)
class TaskSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'kind', 'order', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('title', 'project__name')

@admin.register(TaskTag)
class TaskTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'user__username')

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'task', 'uploaded_at', 'file_size')
    list_filter = ('uploaded_at',)
