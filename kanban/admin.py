from django.contrib import admin
from .models import Workspace, KanbanBoard, KanbanColumn, KanbanCard, KanbanAttachment


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name',)


admin.site.register(KanbanBoard)
admin.site.register(KanbanColumn)
admin.site.register(KanbanCard)
admin.site.register(KanbanAttachment)
