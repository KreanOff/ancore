"""Task screens remain inside the owning space and never invoke legacy Tasks views."""
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.db.models import F, Sum
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from core.frontend import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_GET, require_http_methods

from core.upload_validation import attachment_download_response, validate_comment_attachments, ATTACHMENT_ALLOWED_EXTENSIONS, MAX_COMMENT_ATTACHMENTS, DEFAULT_ATTACHMENT_MAX_SIZE
from dashboard.recent import remember_view
from dashboard.collaboration import comment_mention_metadata, mention_choices
from workplaces.models import Workplace
from workplaces.services import workplace_people
from .access import editable_to, require_editable, visible_to, tree_ids, task_people
from .forms import DetailForm, SubtaskForm, MemberForm, WorkLogForm
from .models import Space, SpaceTask, SpaceTaskFile, SpaceTaskMembership, SpaceTaskWorkLog
from .services import manage_space, record, set_status, space_url, task_subtasks_url, task_url, visible_items
from .views import detail_context, dialog_response, space_object


def task_item(request, space_pk, key):
    space = space_object(request, space_pk)
    return get_object_or_404(visible_items(request), space=space, key=key)


def return_url(request, space):
    params = request.GET.copy()
    params.pop('tab', None)
    params['view'] = params.get('view') if params.get('view') in {'list', 'board', 'backlog', 'timeline', 'overview', 'reports'} else 'list'
    return space_url(request, space, '?') + params.urlencode()


def manages_task(request, task):
    if task.visibility == 'private':
        return task.private_owner_id == request.user.pk or task.memberships.filter(user=request.user, role='admin').exists()
    return manage_space(request, task.space)


def attach_files(task, files, activity, saved_files):
    for uploaded in files:
        file = SpaceTaskFile(task=task, activity=activity, filename=uploaded.name, file_size=uploaded.size)
        file.file.save(uploaded.name, uploaded, save=False)
        saved_files.append(file.file)
        file.save()


def posted_id(request, name):
    value = str(request.POST.get(name, ''))
    if not value.isdecimal() or len(value) > 18 or int(value) < 1:
        raise Http404
    return int(value)


def property_snapshot(task, item):
    def datetime_label(value):
        return date_format(timezone.localtime(value), 'd.m.Y H:i') if value else '—'

    assignee = task.assignee
    return {'tytuł': task.title, 'opis': task.description, 'priorytet': task.get_priority_display(),
            'kategoria zadania': task.get_task_type_display(), 'przypisane do': (assignee.get_full_name() or assignee.email or assignee.username) if assignee else '—',
            'planowane rozpoczęcie': datetime_label(item.start_at),
            'termin wykonania': datetime_label(task.due_at), 'przypomnienie': datetime_label(task.reminder_at),
            'widoczność': 'Prywatne' if task.visibility == 'private' else 'Publiczne',
            'typ zgłoszenia': item.get_work_type_display(), 'tagi': ', '.join(task.tags.values_list('name', flat=True))}


def property_changes(before, after):
    return [{'field': key, 'from_label': before[key] or '—', 'to_label': after[key] or '—'} for key in before if before[key] != after[key]]


def detail_post_data(request, current_form):
    """Merge autosaved fields with live values, including unchanged planning."""
    posted = request.POST.copy()
    if 'autosave_fields' not in posted:
        return posted, set(current_form.fields) | {'status', 'files'}
    try:
        fields = json.loads(posted['autosave_fields'])
    except (ValueError, TypeError):
        raise ValidationError('Nieprawidłowe pola zapisu zadania.')
    allowed = set(current_form.fields) | {'status', 'files'}
    if not isinstance(fields, list) or any(not isinstance(name, str) or name not in allowed for name in fields):
        raise ValidationError('Nieprawidłowe pola zapisu zadania.')
    for name, field in current_form.fields.items():
        if name not in fields:
            value = current_form.initial.get(name, field.initial)
            # Preserve the exact instant (including its offset during a repeated
            # DST hour) when autosave did not edit this datetime.
            value = value.isoformat() if isinstance(value, datetime) else field.widget.format_value(field.prepare_value(value))
            posted.setlist(name, value if isinstance(value, list) else [value] if value is not None else [])
    if 'status' not in fields:
        posted['status'] = current_form.item.status
    return posted, set(fields)


def work_log_context(request, task):
    entries = task.work_logs.select_related('author')
    duration = entries.aggregate(total=Sum(F('ended_at') - F('started_at')))['total'] or timedelta()
    total = int(duration.total_seconds() // 60)
    page = Paginator(entries, 25).get_page(request.POST.get('work_log_page') or request.GET.get('work_log_page'))
    for entry in page:
        hours, minutes = divmod(entry.duration_minutes, 60)
        entry.form_values = json.dumps({'id': entry.pk, 'duration_minutes': entry.duration_minutes,
            'hours': hours, 'minutes': minutes,
            'started_at': timezone.localtime(entry.started_at).strftime('%Y-%m-%dT%H:%M'),
            'ended_at': timezone.localtime(entry.ended_at).strftime('%Y-%m-%dT%H:%M'), 'description': entry.description})
    def url(number):
        params = request.GET.copy()
        params['tab'], params['work_log_page'] = 'work-log', number
        return request.path + '?' + params.urlencode()
    return {'work_log_page': page, 'work_log_total_minutes': total, 'work_log_total_label': f'{total // 60} godz. {total % 60:02d} min',
            'work_log_previous_url': url(page.previous_page_number()) if page.has_previous() else '',
            'work_log_next_url': url(page.next_page_number()) if page.has_next() else ''}



@login_required
@require_http_methods(['GET', 'POST'])
def detail(request, space_pk, key):
    item = task_item(request, space_pk, key)
    task, space = item.task, item.space
    if request.method == 'GET' and task.parent_id:
        remember_view(request, task)
        return redirect(task_subtasks_url(request, task))
    can_edit = editable_to(SpaceTask.objects.filter(pk=task.pk), request.user).exists()
    if request.method == 'POST' and request.POST.get('action') == 'favorite':
        if task.favorited_by.filter(pk=request.user.pk).exists():
            task.favorited_by.remove(request.user)
        else:
            task.favorited_by.add(request.user)
        return redirect(request.get_full_path())
    form = DetailForm(request=request, space=space, item=item)
    log_form = WorkLogForm(prefix="worklog")
    subtask_form = SubtaskForm(request=request, space=space, prefix="subtask")
    error = ''
    tab = request.GET.get('tab', 'main')
    if tab not in {'main', 'subtasks', 'work-log', 'members', 'history'}:
        tab = 'main'
    saved_files = []
    if request.method == 'POST':
        if not can_edit:
            raise PermissionDenied
        try:
            with transaction.atomic():
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
                Space.objects.select_for_update().get(pk=space.pk)
                space = space_object(request, space.pk)
                task = SpaceTask.objects.select_for_update().get(pk=task.pk)
                require_editable(SpaceTask.objects.filter(pk=task.pk), request.user)
                item = task_item(request, space_pk, key)
                action = request.POST.get('action', 'save')
                if action == 'save':
                    history_after = task.activities.order_by('-pk').values_list('pk', flat=True).first() or 0
                    files = request.FILES.getlist('files')
                    current_form = DetailForm(request=request, space=space, item=item)
                    posted, changed_fields = detail_post_data(request, current_form)
                    form = DetailForm(posted, request=request, space=space, item=item,
                                      changed_fields=changed_fields if 'autosave_fields' in posted else None)
                    validate_comment_attachments(files)
                    if form.is_valid():
                        data = form.cleaned_data
                        old = property_snapshot(task, item)
                        old_relations_dates = (task.assignee_id, task.due_at, task.reminder_at)
                        planning_fields = ('work_type', 'team_id', 'sprint_id', 'epic_id', 'points', 'start_at', 'in_backlog', 'custom_values')
                        old_planning = [getattr(item, name) for name in planning_fields]
                        previous = {'title': task.title, 'priority': task.priority, 'work_type': item.work_type}
                        target = form.data.get('status', item.status)
                        set_status(request, item, target)
                        task.refresh_from_db()
                        for name in ('title', 'description', 'priority', 'assignee', 'due_at', 'task_type', 'reminder_at'):
                            if name in changed_fields:
                                setattr(task, name, data[name])
                        if 'visibility' in changed_fields:
                            task.visibility = data['visibility']
                        task.private_owner = (task.private_owner or request.user) if task.visibility == 'private' else None
                        task.save()
                        if task.visibility == 'public':
                            task.memberships.all().delete()
                        if 'tags' in changed_fields:
                            task.tags.set(data['tags'])
                        item.refresh_from_db()
                        for name in ('work_type', 'team', 'sprint', 'epic', 'points', 'start_at', 'in_backlog'):
                            if name in data and (name in changed_fields or name == 'in_backlog' and 'sprint' in changed_fields):
                                setattr(item, name, data[name])
                        custom_values = {f['key']: str(data['custom_' + f['key']]) if data.get('custom_' + f['key']) is not None else ''
                                         for f in space.configuration.settings.get('fields', []) if 'custom_' + f['key'] in changed_fields}
                        item.custom_values = {**item.custom_values, **custom_values} if 'autosave_fields' in posted else custom_values
                        item.save()
                        changes = property_changes(old, property_snapshot(task, item))
                        if (changes or old_relations_dates != (task.assignee_id, task.due_at, task.reminder_at)
                                or old_planning != [getattr(item, name) for name in planning_fields]):
                            record(item, request.user, 'updated', 'zaktualizował zadanie', {'before': previous, 'changes': changes})
                        if files:
                            attach_files(task, files, None, saved_files)
                            record(item, request.user, 'attachments_added', 'dodał załączniki')
                        saved_history = list(task.activities.filter(pk__gt=history_after, kind='system').select_related('actor'))
                    else:
                        raise ValidationError('Popraw oznaczone pola.')
                elif action in {'comment', 'attachment'}:
                    files = request.FILES.getlist('files') + request.FILES.getlist('comment_attachments')
                    validate_comment_attachments(files)
                    raw_text = request.POST.get('message') or request.POST.get('activity_comment') or ''
                    text = raw_text.replace('\r\n', '\n').strip()
                    if not text and not files:
                        raise ValidationError('Wpisz treść komentarza lub dodaj plik.')
                    activity = record(item, request.user, 'commented' if action == 'comment' else 'attachments_added', text or 'dodał załączniki', comment_mention_metadata(task, raw_text, request.POST.get('activity_mentions')) if action == 'comment' else {})
                    if action == 'comment':
                        activity.kind = 'comment'
                        activity.save(update_fields=['kind'])
                    attach_files(task, files, activity if action == 'comment' else None, saved_files)
                elif action == 'delete_file':
                    file = get_object_or_404(task.attachments, pk=posted_id(request, 'file_id'))
                    file.delete()
                    record(item, request.user, 'attachments_deleted', 'usunął załącznik')
                elif action in {'subtask', 'create_subtask_modal'}:
                    # Historical direct POSTs stay supported; the modal submits scoped fields.
                    posted = request.POST.copy()
                    if action == 'subtask':
                        posted['subtask-title'] = posted.get('title', '')
                        posted['subtask-status'] = space.statuses[0]['key']
                        posted['subtask-visibility'] = 'public'
                    subtask_form = SubtaskForm(posted, request=request, space=space, prefix='subtask')
                    if not subtask_form.is_valid():
                        raise ValidationError('Popraw dane podzadania.')
                    data = subtask_form.cleaned_data
                    status_key = data['status']
                    status = next(status for status in space.statuses if status['key'] == status_key)
                    child = SpaceTask(space=space, parent=task, created_by=request.user,
                                      private_owner=request.user if data['visibility'] == 'private' else None,
                                      status=status['category'], **{name: data[name] for name in (
                                          'title', 'description', 'visibility', 'priority', 'assignee', 'due_at',
                                      )})
                    child._activity_actor = request.user
                    child.save()
                    child_item = child.work_item
                    child_item.status = status['key']
                    for name in ('work_type', 'start_at', 'points'):
                        setattr(child_item, name, data[name])
                    child_item.save(update_fields=['status', 'work_type', 'start_at', 'points'])
                    record(item, request.user, 'subtask_created', 'dodał podzadanie', {'subtask_pk': child.pk, 'subtask_title': child.title})
                    if action == 'subtask':
                        return redirect(task_url(request, child))
                elif action == 'delete_subtasks':
                    try:
                        ids = {int(pk) for pk in request.POST.getlist('subtask_ids')}
                    except (ValueError, TypeError):
                        raise Http404
                    selected = visible_to(SpaceTask.objects.filter(pk__in=tree_ids(task.subtasks.all())), request.user).filter(pk__in=ids)
                    if not ids or selected.count() != len(ids):
                        raise Http404
                    descendants = SpaceTask.objects.filter(pk__in=tree_ids(selected))
                    require_editable(descendants, request.user)
                    descendants.delete()
                    record(item, request.user, 'subtasks_deleted', 'usunął podzadania', {'count': len(ids)})
                elif action in {'work-log', 'add_work_log', 'edit_work_log', 'delete_work_log'}:
                    entry = None if action in {'work-log', 'add_work_log'} else get_object_or_404(task.work_logs.select_for_update(), pk=posted_id(request, 'work_log_id'))
                    log_form = WorkLogForm(request.POST, instance=entry, prefix='worklog' if action != 'work-log' else None)
                    if action == 'delete_work_log':
                        minutes, entry_id = entry.duration_minutes, entry.pk
                        entry.delete()
                        activity_action, message = 'work_log_deleted', 'usunął wpis czasu'
                    else:
                        if not log_form.is_valid():
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return JsonResponse({'status': 'error', 'message': 'Sprawdź dane wpisu.', 'form_html': render_to_string('tasks/includes/work_log_fields.html', {'work_log_form': log_form}, request=request)}, status=400)
                            raise ValidationError('Popraw dane dziennika pracy.')
                        entry = log_form.save(commit=False)
                        if not entry.pk:
                            entry.task, entry.author = task, request.user
                        entry.save()
                        minutes, entry_id = entry.duration_minutes, entry.pk
                        activity_action, message = ('work_log_added', 'dodał wpis czasu') if action in {'work-log', 'add_work_log'} else ('work_log_updated', 'zmienił wpis czasu')
                    activity = record(item, request.user, activity_action, f'{message} ({minutes} min)', {'work_log_id': entry_id, 'minutes': minutes})
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'success', 'message': 'Usunięto wpis.' if action == 'delete_work_log' else 'Zapisano wpis.',
                            'work_log_html': render_to_string('tasks/includes/work_log_list.html', {'can_edit_task': True, **work_log_context(request, task)}, request=request),
                            'activity_html': render_to_string('tasks/includes/task_activity_item.html', {'item': activity}, request=request)})
                elif action == 'delete':
                    descendants = SpaceTask.objects.filter(pk__in=tree_ids(SpaceTask.objects.filter(pk=task.pk)))
                    require_editable(descendants, request.user)
                    task.delete()
                    return redirect(return_url(request, space))
                else:
                    raise Http404
            if action == 'save' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Only activities created by this transaction are returned to the open feed.
                payload = {'status': 'success', 'task': {'title': task.title,
                    'completion_date': date_format(timezone.localtime(task.completion_date), 'd.m.Y, H:i') if task.completion_date else ''},
                    'activity_html': ''.join(render_to_string('tasks/includes/task_activity_item.html', {'item': activity}, request=request) for activity in saved_history),
                    'attachments_html': render_to_string('spaces/task_attachments.html', {'files': task.attachments.filter(activity__isnull=True), 'space_url': space_url(request, space), 'item': item, 'can_edit_task': can_edit}, request=request) if files else None}
                if old['widoczność'] != property_snapshot(task, item)['widoczność']:
                    from .task_team import payload as team_payload
                    payload['team'] = team_payload(request, task)
                return JsonResponse(payload)
            if action == 'comment' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'activity_html': render_to_string('spaces/task_comment.html', {'comment': activity, 'item': item, 'space_url': space_url(request, space)}, request=request)})
            return redirect(request.get_full_path())
        except ValidationError as exc:
            for file in saved_files:
                file.storage.delete(file.name)
            error = ' '.join(exc.messages)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error, 'errors': form.errors.get_json_data()}, status=400)
        except Exception:
            for file in saved_files:
                file.storage.delete(file.name)
            raise
    for field in form.fields.values():
        field.widget.attrs['form'] = 'space-task-form'
    form.fields['description'].widget.attrs['placeholder'] = 'Wprowadź opis zadania...'
    form.fields['assignee'].label = 'Przypisane do'
    form.fields['tags'].widget.attrs.update({'data-ancore-custom-select-empty-label': 'Tagi', 'data-ancore-custom-select-icon': 'tag'})
    if not can_edit:
        for field in form.fields.values():
            field.disabled = True
    # The task uses the shared issue shell while its URL and return keep space context.
    context = detail_context(request, space, request.GET.get('view', 'list'))
    tabs = []
    for value, label, icon in [('main', 'Główna', 'file-text'), ('subtasks', 'Podzadania', 'list-checks'), ('work-log', 'Dziennik pracy', 'clock'), ('members', 'Członkowie', 'users'), ('history', 'Historia', 'rotate-ccw')]:
        params = request.GET.copy()
        params['tab'] = value
        tabs.append({'key': value, 'label': label, 'icon': icon, 'url': request.path + '?' + params.urlencode()})
    context.update(item=item, task=task, form=form, error=error, can_edit_task=can_edit,
                   back_url=return_url(request, space), task_tab=tab, task_tabs=tabs, log_form=log_form, work_log_form=log_form, subtask_form=subtask_form,
                   work_log_url=request.get_full_path(), work_log_modal_open=bool(log_form.errors), subtask_modal_open=bool(subtask_form.errors),
                   task_edit_url=space_url(request, space, f'tasks/{key}/edit/'),
                   member_edit_url=space_url(request, space, f'tasks/{key}/members/'),
                   can_manage_task=can_edit and manages_task(request, task),
                   subtasks=visible_items(request).filter(task_id__in=tree_ids(task.subtasks.all())),
                   comments=visible_to(task.activities.filter(kind='comment'), request.user).select_related('actor').prefetch_related('images'),
                   history=visible_to(task.activities.filter(kind='system'), request.user).select_related('actor'),
                   files=task.attachments.filter(activity__isnull=True), logs=task.work_logs.select_related('author'),
                   task_members=task.memberships.filter(user__in=workplace_people(request.workplace)).select_related('user'))
    context['is_favorite'] = task.favorited_by.filter(pk=request.user.pk).exists()
    context['detail_status'] = request.POST.get('status', item.status) if error else item.status
    context.update(work_log_context(request, task))
    from .task_team import team_context
    context.update(team_context(request, task))
    from .views import decorate_items
    children = decorate_items(request, list(context['subtasks']))
    for child in children:
        child.url = task_url(request, child.task)
        child.status_label = next((status['label'] for status in space.statuses if status['key'] == child.status), child.status)
    context['subtask_status_groups'] = [{'status': status['category'], 'label': status['label'], 'tasks': [child for child in children if child.status == status['key']]} for status in space.statuses]
    context['subtask_count'] = len(children)
    context['planning_has_errors'] = any(field.errors for field in form if field.name not in {'title', 'description', 'priority', 'tags', 'work_type', 'assignee', 'start_at', 'due_at', 'task_type', 'reminder_at', 'visibility'})
    context.update(mention_people=mention_choices(task), comment_placeholder='Napisz komentarz; wpisz @ i imię osoby...', comment_image_limit=MAX_COMMENT_ATTACHMENTS,
                   comment_image_max_size=DEFAULT_ATTACHMENT_MAX_SIZE, comment_attachment_accept=','.join(sorted(ATTACHMENT_ALLOWED_EXTENSIONS)),
                   comment_draft=request.POST.get('message') or request.POST.get('activity_comment', ''))
    remember_view(request, task)
    return render(request, 'spaces/task_detail.html', context, status=400 if error else 200)


@login_required
@require_http_methods(['GET', 'POST'])
def members(request, space_pk, key):
    item = task_item(request, space_pk, key)
    task = item.task
    if not manages_task(request, task) or not editable_to(SpaceTask.objects.filter(pk=task.pk), request.user).exists():
        raise PermissionDenied
    form = MemberForm(request.POST if request.method == 'POST' else None, request=request)
    form.fields['person'].queryset = task_people(task).exclude(pk=task.private_owner_id)
    from django import forms
    form.fields['visibility'] = forms.ChoiceField(label='Widoczność', choices=SpaceTask._meta.get_field('visibility').choices, initial=task.visibility)
    form.fields['person'].required = False
    if task.visibility == 'private' and task.private_owner_id != request.user.pk:
        form.fields['visibility'].disabled = True
        form.fields['role'].choices = [('member', 'Członek'), ('observer', 'Obserwator')]
    form.style()
    url = task_url(request, task)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            Space.objects.select_for_update().get(pk=item.space_id)
            item = task_item(request, space_pk, key)
            require_editable(SpaceTask.objects.filter(pk=task.pk), request.user)
            task = SpaceTask.objects.select_for_update().get(pk=task.pk)
            if not manages_task(request, task):
                raise PermissionDenied
            person = form.cleaned_data.get('person')
            if person and not task_people(task).filter(pk=person.pk).exists():
                form.add_error('person', 'Ta osoba nie ma już dostępu do przestrzeni lub rodzica zadania.')
                return dialog_response(request, form, 'Dostęp do zadania', url)
            membership = get_object_or_404(task.memberships, pk=posted_id(request, 'remove_member')) if request.POST.get('remove_member') else None
            if membership and membership.user_id == task.private_owner_id:
                raise PermissionDenied
            next_owner_id = (task.private_owner_id or request.user.pk) if form.cleaned_data['visibility'] == 'private' else None
            if person and person.pk == next_owner_id:
                form.add_error('person', 'Właściciel zadania ma dostęp bez osobnego członkostwa.')
                return dialog_response(request, form, 'Dostęp do zadania', url)
            existing = task.memberships.filter(user=form.cleaned_data.get('person')).first()
            if task.visibility == 'private' and task.private_owner_id != request.user.pk and (membership or existing) and (membership or existing).role == 'admin':
                raise PermissionDenied
            task.visibility = form.cleaned_data['visibility']
            task.private_owner = (task.private_owner or request.user) if task.visibility == 'private' else None
            task.save(update_fields=['visibility', 'private_owner'])
            if task.visibility == 'public':
                task.memberships.all().delete()
            elif membership:
                membership.delete()
            elif form.cleaned_data.get('person'):
                SpaceTaskMembership.objects.update_or_create(task=task, user=form.cleaned_data['person'], defaults={'role': form.cleaned_data['role']})
            record(item, request.user, 'updated', 'zmienił dostęp do zadania')
        return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Dostęp do zadania', url)


@login_required
@require_GET
def download(request, space_pk, key, file_pk):
    item = task_item(request, space_pk, key)
    file = get_object_or_404(SpaceTaskFile, task=item.task, pk=file_pk)
    try:
        response = attachment_download_response(file, inline=bool(file.activity_id and file.is_image()))
    except FileNotFoundError:
        raise Http404
    response['Cache-Control'] = 'private, no-store'
    return response
