"""Compatibility links for imported records, checked against live Space ACLs."""
from django.http import Http404, JsonResponse
from django.db.models import Q
from django.shortcuts import redirect

from tasks.models import Task, TaskAttachment, TaskCommentImage, TaskProject, TaskSection
from workplaces.services import workspace_owner
from .models import LegacyKanbanLink, SpaceTaskFile, WorkItem
from .services import app_url, space_url, task_url, visible_items, visible_spaces


class LegacyKanbanMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if request.user.is_authenticated and match.app_name in {'tasks', 'workplace_tasks'}:
            owner = workspace_owner(request)
            from tasks.tagging import TAG_ACTIONS
            if request.GET.get('view') == 'tags' or request.POST.get('action') in TAG_ACTIONS:
                raise Http404
            if request.method not in {'GET', 'HEAD'}:
                return JsonResponse({'error': 'Starsze widoki zostały wycofane. Otwórz Przestrzenie.', 'url': app_url(request)}, status=409)
            if match.url_name in {'tasks', 'task_group'}:
                section_id = view_kwargs.get('section_id') or request.GET.get('section')
                project_id = request.GET.get('project')
                if section_id or project_id:
                    source_id = str(section_id or project_id)
                    if not source_id.isdecimal() or len(source_id) > 18:
                        raise Http404
                    projects = TaskProject.objects.filter(user=owner, workplace=request.workplace)
                    if section_id:
                        projects = projects.filter(pk__in=TaskSection.objects.filter(pk=source_id).values('project_id'))
                    else:
                        projects = projects.filter(pk=source_id)
                    space = visible_spaces(request).filter(project__in=projects).first()
                    if not space:
                        raise Http404
                    return redirect(space_url(request, space, '?view=list' if section_id else ''))
                return None
            if match.url_name in {'view-task', 'view-subtask'}:
                source = Task.objects.filter(user=owner, workplace=request.workplace)
                task_pk = request.GET.get('task_pk', '')
                source = source.filter(pk=task_pk) if task_pk.isdecimal() and len(task_pk) < 19 else source.none() if task_pk else source.filter(task_id=view_kwargs['task_id'])
                imported = WorkItem.objects.filter(legacy_task__in=source, task__isnull=False).first()
                if imported:
                    item = visible_items(request).filter(pk=imported.pk).first()
                    if not item:
                        raise Http404
                    url = task_url(request, item.task)
                    return redirect(url)
            else:
                attachment = match.url_name == 'download_attachment'
                model = TaskAttachment if attachment else TaskCommentImage
                source = model.objects.filter(pk=view_kwargs.get('attachment_id') if attachment else view_kwargs.get('image_id')).first()
                task = source.task if source and attachment else source.activity.task if source else None
                if task and (task.user_id, task.workplace_id) == (owner.pk, request.workplace.pk):
                    item = visible_items(request).filter(legacy_task=task).first()
                    if item:
                        file = SpaceTaskFile.objects.filter(task=item.task, file=source.file.name, legacy_storage=attachment).first()
                        if not file:
                            raise Http404
                        return redirect(space_url(request, item.space, f'tasks/{item.key}/files/{file.pk}/'))
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
            item = visible_items(request).filter(legacy_task_id=link.target_id).first()
            if not item:
                raise Http404
            return redirect(task_url(request, item.task))
        if name in {'download_attachment', 'comment_image'}:
            attachment = name == 'download_attachment'
            kind, model = ('attachment', TaskAttachment) if attachment else ('comment', TaskCommentImage)
            source_id = view_kwargs.get('attachment_id') if attachment else view_kwargs.get('image_id')
            link = LegacyKanbanLink.objects.filter(kind=kind, source_id=source_id).first()
            path = 'task' if attachment else 'activity__task'
            files = model.objects.filter(**{path + '__user': owner, path + '__workplace': request.workplace})
            imported = files.filter(pk=link.target_id).first() if link else None
            task_id = imported.task_id if imported and attachment else imported.activity.task_id if imported else None
            item = visible_items(request).filter(legacy_task_id=task_id).first() if imported else None
            if not item:
                raise Http404
            file = SpaceTaskFile.objects.filter(task=item.task, file=imported.file.name, legacy_storage=attachment).first()
            if not file:
                raise Http404
            return redirect(space_url(request, item.space, f'tasks/{item.key}/files/{file.pk}/'))
        section_id = view_kwargs.get('section_id') or request.GET.get('section')
        project_id = request.GET.get('project')
        if section_id or project_id:
            source_id = str(section_id or project_id)
            if not source_id.isdecimal() or len(source_id) > 18:
                raise Http404
            link = scope.filter(kind='section' if section_id else 'project', source_id=source_id).first()
            space = visible_spaces(request).filter(pk=link.space_id).first() if link else None
            if not space:
                raise Http404
            suffix = '?view=board' if section_id else ''
            return redirect(space_url(request, space, suffix))
        return redirect(app_url(request))
