from django.contrib import admin
from .models import KanbanBoard, KanbanColumn, KanbanCard, KanbanAttachment

admin.site.register(KanbanBoard)
admin.site.register(KanbanColumn)
admin.site.register(KanbanCard)
admin.site.register(KanbanAttachment)
