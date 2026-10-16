"""Read-only compatibility links for the retired projects, groups and tasks."""
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import path

from spaces.services import app_url

app_name = 'tasks'


@login_required
def retired_tasks(request, **kwargs):
    # Imported details and files are resolved by LegacyKanbanMiddleware using
    # current Space ACLs. Unmapped records never reach historical views.
    if request.method not in {'GET', 'HEAD'}:
        return JsonResponse({'error': 'Starsze widoki zostały wycofane. Otwórz Przestrzenie.', 'url': app_url(request)}, status=409)
    if request.resolver_match.url_name == 'tasks' and request.GET.get('view') != 'tags':
        return redirect(app_url(request))
    raise Http404


urlpatterns = [
    path('', retired_tasks, name='tasks'),
    path('groups/<int:section_id>/', retired_tasks, name='task_group'),
    path('view-task/<int:task_id>/', retired_tasks, name='view-task'),
    path('view-subtask/<int:task_id>/', retired_tasks, name='view-subtask'),
    path('attachments/<int:attachment_id>/download/', retired_tasks, name='download_attachment'),
    path('comment-images/<int:image_id>/', retired_tasks, name='comment_image'),
]
