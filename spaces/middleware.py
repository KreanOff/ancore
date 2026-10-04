"""Compatibility links for imported Kanban records, checked against live Task ACLs."""
from django.http import Http404, JsonResponse
from django.db.models import Q
from django.shortcuts import redirect

from tasks.access import visible_to
from tasks.models import Task, TaskAttachment, TaskCommentImage
from workplaces.services import workspace_owner
from .models import LegacyKanbanLink
from .services import app_url, task_url, visible_spaces


class LegacyKanbanMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if not request.user.is_authenticated or match.app_name not in {'kanban', 'workplace_kanban'}:
            return None
        owner = workspace_owner(request)
        from kanban.models import Kanban, KanbanProject, KanbanSection
        projects = KanbanProject.objects.filter(user=owner, workplace=request.workplace)
        cards = Kanban.objects.filter(user=owner, workplace=request.workplace)
        scope = LegacyKanbanLink.objects.filter(
            Q(kind='project', source_id__in=projects.values('pk')) |
            Q(kind='section', source_id__in=KanbanSection.objects.filter(project__in=projects).values('pk')) |
            Q(kind='task', source_id__in=cards.values('pk'))
        )
        if request.method not in {'GET', 'HEAD'}:
            return JsonResponse({'error': 'Kanban został przeniesiony do Przestrzeni. Otwórz zadanie w nowym widoku.', 'url': app_url(request)}, status=409)
        name = match.url_name
        if name in {'view-task', 'view-subtask'}:
            from kanban.models import Kanban
            source = Kanban.objects.filter(user=owner, workplace=request.workplace)
            task_pk = request.GET.get('task_pk', '')
            if task_pk:
                source = source.filter(pk=task_pk) if task_pk.isdecimal() and len(task_pk) < 19 else source.none()
            else:
                source = source.filter(task_id=view_kwargs['task_id'])
            link = LegacyKanbanLink.objects.filter(kind='task', source_id__in=source.values('pk')).first()
            if not link:
                raise Http404
            task = visible_to(Task.objects.filter(user=owner, workplace=request.workplace), request.user).filter(pk=link.target_id).first()
            if not task:
                raise Http404
            return redirect(task_url(request, task))
        if name in {'download_attachment', 'comment_image'}:
            attachment = name == 'download_attachment'
            kind, model = ('attachment', TaskAttachment) if attachment else ('comment', TaskCommentImage)
            source_id = view_kwargs.get('attachment_id') if attachment else view_kwargs.get('image_id')
            link = LegacyKanbanLink.objects.filter(kind=kind, source_id=source_id).first()
            path = 'task' if attachment else 'activity__task'
            files = model.objects.filter(**{path + '__user': owner, path + '__workplace': request.workplace})
            if not link or not visible_to(files.filter(pk=link.target_id), request.user).exists():
                raise Http404
            suffix = f'attachments/{link.target_id}/download/' if attachment else f'comment-images/{link.target_id}/'
            return redirect(app_url(request, suffix, 'tasks'))
        section_id = view_kwargs.get('section_id') or request.GET.get('section')
        project_id = request.GET.get('project')
        if section_id or project_id:
            source_id = str(section_id or project_id)
            if not source_id.isdecimal() or len(source_id) > 18:
                raise Http404
            link = scope.filter(kind='section' if section_id else 'project', source_id=source_id).first()
            if not link or not visible_spaces(request).filter(pk=link.space_id).exists():
                raise Http404
            if section_id:
                from tasks.models import TaskSection
                if not visible_to(TaskSection.objects.filter(pk=link.target_id), request.user).exists():
                    raise Http404
            suffix = f'{link.space_id}/' + (f'?view=board&group={link.target_id}' if section_id else '')
            return redirect(app_url(request, suffix))
        return redirect(app_url(request))
