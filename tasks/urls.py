from django.urls import path
from .views import tasks, kanban, calendar

app_name = 'tasks'

urlpatterns = [
    path('', tasks.tasks, name='tasks'),
    path('create-task/', tasks.create_task, name='create_task'),
    path('edit-task/<int:task_id>/', tasks.edit_task, name='edit_task'),
    path('view-task/<int:task_id>/', tasks.view_task, name='view-task'),
    path('update/<int:task_id>/', tasks.update_task_status, name='update_task_status'),
    path('delete-attachment/<int:attachment_id>/', tasks.delete_attachment, name='delete_attachment'),
    path('delete/<int:task_id>/', tasks.delete_task, name='delete_task'),
    path('delete/', tasks.delete_tasks, name='delete_tasks'),
    path('bulk-update-status/', tasks.bulk_update_status, name='bulk_update_status'),
    path('kanban/', kanban.kanban, name='kanban'),
    path('calendar/', calendar.calendar, name='calendar'),
]
