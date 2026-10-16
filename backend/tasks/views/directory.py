from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from tasks.access import visible_to
from tasks.models import Task, TaskProject, TaskSection
from workplaces.services import workspace_owner


@login_required
@require_POST
def directory_favorite(request, kind, object_id):
    """Favorites are personal preferences, including for read-only members."""
    if kind == 'project':
        queryset = TaskProject.objects.filter(user=workspace_owner(request), workplace=request.workplace)
    elif kind == 'section':
        queryset = TaskSection.objects.filter(
            project__user=workspace_owner(request), project__workplace=request.workplace,
        )
    elif kind == 'task':
        queryset = Task.objects.filter(
            user=workspace_owner(request), workplace=request.workplace, parent__isnull=True,
        )
    else:
        raise Http404
    item = get_object_or_404(visible_to(queryset, request.user), pk=object_id)
    action = request.POST.get('favorite_action')
    if action not in {'add', 'remove'}:
        return JsonResponse({'error': 'Nieprawidłowa akcja ulubionych.'}, status=400)
    if action == 'add':
        item.favorited_by.add(request.user)
    else:
        item.favorited_by.remove(request.user)
    return JsonResponse({'is_favorite': action == 'add'})
