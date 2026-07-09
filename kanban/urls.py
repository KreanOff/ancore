from django.urls import path
from .views import tasks

app_name = 'kanban'

urlpatterns = [
    path('', tasks.tasks, name='tasks'),
    path('groups/<int:section_id>/', tasks.task_group, name='task_group'),
    path('view-task/<int:task_id>/', tasks.view_task, name='view-task'),
    path('view-subtask/<int:task_id>/', tasks.view_subtask, name='view-subtask'),
    path('update/<int:task_id>/', tasks.update_task_status, name='update_task_status'),
    path('groups/<int:section_id>/reorder-columns/', tasks.reorder_board_columns, name='reorder_board_columns'),
    path('attachments/<int:attachment_id>/download/', tasks.download_attachment, name='download_attachment'),
    path('delete-attachment/<int:attachment_id>/', tasks.delete_attachment, name='delete_attachment'),
    path('delete/<int:task_id>/', tasks.delete_task, name='delete_task'),
    path('delete/', tasks.delete_tasks, name='delete_tasks'),
    path('bulk-update-status/', tasks.bulk_update_status, name='bulk_update_status'),
]
