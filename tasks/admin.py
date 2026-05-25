from django.contrib import admin
from .models import Task, TaskAttachment, TaskProject, TaskSection

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'title', 'section', 'user', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'description')
    inlines = [TaskAttachmentInline]


class TaskSectionInline(admin.TabularInline):
    model = TaskSection
    extra = 1


@admin.register(TaskProject)
class TaskProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'user', 'created_at')
    search_fields = ('name', 'code')
    inlines = [TaskSectionInline]


@admin.register(TaskSection)
class TaskSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'kind', 'order', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('title', 'project__name')

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'task', 'uploaded_at', 'file_size')
    list_filter = ('uploaded_at',)
