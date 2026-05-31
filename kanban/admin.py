from django.contrib import admin
from .models import Kanban, KanbanAttachment, KanbanBoardColumn, KanbanProject, KanbanSection, KanbanTag

class KanbanAttachmentInline(admin.TabularInline):
    model = KanbanAttachment
    extra = 1

@admin.register(Kanban)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'title', 'section', 'user', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'description')
    inlines = [KanbanAttachmentInline]


class KanbanSectionInline(admin.TabularInline):
    model = KanbanSection
    extra = 1


class KanbanBoardColumnInline(admin.TabularInline):
    model = KanbanBoardColumn
    extra = 1


@admin.register(KanbanProject)
class KanbanProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'user', 'created_at')
    search_fields = ('name', 'code')
    inlines = [KanbanSectionInline]


@admin.register(KanbanSection)
class KanbanSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'kind', 'order', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('title', 'project__name')
    inlines = [KanbanBoardColumnInline]


@admin.register(KanbanBoardColumn)
class KanbanBoardColumnAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'order', 'is_done', 'created_at')
    list_filter = ('is_done', 'created_at')
    search_fields = ('title', 'section__title', 'section__project__name')

@admin.register(KanbanTag)
class KanbanTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'user__username')

@admin.register(KanbanAttachment)
class KanbanAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'task', 'uploaded_at', 'file_size')
    list_filter = ('uploaded_at',)
