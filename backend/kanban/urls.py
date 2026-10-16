"""Read-only compatibility addresses; the old Kanban application is retired."""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import path

app_name = 'kanban'


@login_required
def retired_kanban(request, **kwargs):
    # LegacyKanbanMiddleware resolves imported objects using current Task ACLs.
    # Never fall back to the historical views, even without an import mapping.
    raise Http404


urlpatterns = [
    path('', retired_kanban, name='tasks'),
    path('groups/<int:section_id>/', retired_kanban, name='task_group'),
    path('view-task/<int:task_id>/', retired_kanban, name='view-task'),
    path('view-subtask/<int:task_id>/', retired_kanban, name='view-subtask'),
    path('attachments/<int:attachment_id>/download/', retired_kanban, name='download_attachment'),
    path('comment-images/<int:image_id>/', retired_kanban, name='comment_image'),
]
