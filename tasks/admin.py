from django.contrib import admin
from .models import Task, TaskAttachment, TaskProject, TaskSection

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'title', 'section', 'user', 'status', 'priority', 'due_at', 'created_at')
    list_filter = ('status', 'priority', 'due_at', 'created_at')
    search_fields = ('title', 'description')
    inlines = [TaskAttachmentInline]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'tags':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(space__isnull=False)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class TaskSectionInline(admin.TabularInline):
    model = TaskSection
    extra = 1


@admin.register(TaskProject)
class TaskProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority', 'due_at', 'company', 'user', 'created_at')
    list_filter = ('priority', 'due_at', 'created_at')
    search_fields = ('name', 'code', 'company__name')
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
