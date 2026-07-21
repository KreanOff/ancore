from django.contrib import admin
from .models import Kanban, KanbanAttachment, KanbanBoardColumn, KanbanProject, KanbanProjectNote, KanbanSection

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


class KanbanProjectNoteInline(admin.TabularInline):
    model = KanbanProjectNote
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(KanbanProject)
class KanbanProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'user', 'created_at')
    search_fields = ('name', 'code')
    inlines = [KanbanSectionInline, KanbanProjectNoteInline]


@admin.register(KanbanProjectNote)
class KanbanProjectNoteAdmin(admin.ModelAdmin):
    list_display = ('project', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('project__name', 'message', 'author__username', 'author__first_name', 'author__last_name')


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

@admin.register(KanbanAttachment)
class KanbanAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'task', 'uploaded_at', 'file_size')
    list_filter = ('uploaded_at',)
