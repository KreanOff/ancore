from django.urls import path
from dashboard.collaboration import follow_object
from .views import tasks
from .views.project_templates import edit_project_template, project_templates
from .views.project_team import project_team, project_candidates, project_invitation_response

app_name = 'tasks'

urlpatterns = [
    path('projects/<int:project_id>/team/', project_team, name='project_team'),
    path('projects/<int:project_id>/team/candidates/', project_candidates, name='project_candidates'),
    path('project-invitations/<int:invitation_id>/respond/', project_invitation_response, name='project_invitation_response'),
    path('comment-images/<int:image_id>/', tasks.comment_image, name='comment_image'),
    path('follow/<str:kind>/<int:object_id>/', follow_object, {'app': 'tasks'}, name='follow_object'),
    path('', tasks.tasks, name='tasks'),
    path('templates/', project_templates, name='project_templates'),
    path('templates/<int:template_id>/edit/', edit_project_template, name='edit_project_template'),
    path('groups/<int:section_id>/', tasks.task_group, name='task_group'),
    path('view-task/<int:task_id>/', tasks.view_task, name='view-task'),
    path('view-subtask/<int:task_id>/', tasks.view_subtask, name='view-subtask'),
    path('update/<int:task_id>/', tasks.update_task_status, name='update_task_status'),
    path('attachments/<int:attachment_id>/download/', tasks.download_attachment, name='download_attachment'),
    path('delete-attachment/<int:attachment_id>/', tasks.delete_attachment, name='delete_attachment'),
    path('delete/<int:task_id>/', tasks.delete_task, name='delete_task'),
    path('delete/', tasks.delete_tasks, name='delete_tasks'),
    path('bulk-update-status/', tasks.bulk_update_status, name='bulk_update_status'),
]
