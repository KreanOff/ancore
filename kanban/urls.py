from django.urls import path
from dashboard.collaboration import follow_object
from .views import tasks
from .views.directory import directory_favorite
from .views.project_team import project_team, project_candidates
from .views.section_team import section_team, section_candidates

app_name = 'kanban'

urlpatterns = [
    path('projects/<int:project_id>/team/', project_team, name='project_team'),
    path('projects/<int:project_id>/team/candidates/', project_candidates, name='project_candidates'),
    path('groups/<int:section_id>/team/', section_team, name='section_team'),
    path('groups/<int:section_id>/team/candidates/', section_candidates, name='section_candidates'),
    path('favorites/<str:kind>/<int:object_id>/', directory_favorite, name='directory_favorite'),
    path('comment-images/<int:image_id>/', tasks.comment_image, name='comment_image'),
    path('follow/<str:kind>/<int:object_id>/', follow_object, {'app': 'kanban'}, name='follow_object'),
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
