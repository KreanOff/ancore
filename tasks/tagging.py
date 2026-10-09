"""Tags available exclusively within a visible space."""
import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from workplaces.services import workspace_owner
from .access import editable_to, visible_to
from .models import TaskProject, TaskTag, TaskTagNote


TAG_ACTIONS = {'create_tag', 'edit_tag', 'delete_tag', 'add_tag_note',
               'update_tag_notes', 'edit_tag_note', 'delete_tag_note'}


def tags_in_scope(user, workplace, space):
    if space is None:
        return TaskTag.objects.none()
    return TaskTag.objects.filter(user=user, workplace=workplace, space=space)


def _valid_pk(value):
    return str(value).isdecimal() and len(str(value)) < 19


def _posted_pk(request, name):
    value = request.POST.get(name, '')
    if not _valid_pk(value):
        raise Http404
    return int(value)


def visible_tags(request):
    projects = visible_to(TaskProject.objects.filter(
        user=workspace_owner(request), workplace=request.workplace,
    ), request.user)
    return TaskTag.objects.filter(user=workspace_owner(request), workplace=request.workplace,
                                  space__project__in=projects)


def form_tags(form, user, workplace, project=None, section=None):
    """Use the saved location for edits and validated relation choices for creation."""
    if form.instance.pk:
        section = form.instance.section
        project = section.project if section else None
    elif form.is_bound:
        section_field = form.fields.get('section')
        section_id = form.data.get(form.add_prefix('section'), '')
        section = section_field.queryset.filter(pk=section_id).first() if section_field and _valid_pk(section_id) else None
        project_field = form.fields.get('project')
        project_id = form.data.get(form.add_prefix('project'), '')
        if project_field:
            project = project_field.queryset.filter(pk=project_id).first() if _valid_pk(project_id) else None
        parent_field = form.fields.get('parent')
        parent_id = form.data.get(form.add_prefix('parent'), '')
        if parent_field and _valid_pk(parent_id):
            parent = parent_field.queryset.filter(pk=parent_id).first()
            if parent:
                section = parent.section
    else:
        section = section or getattr(form.instance, 'section', None)
    if section:
        project = section.project
    space = getattr(project, 'space', None) if project else None
    # Picker changes remain local; serialize only projects visible to the viewer.
    projects = visible_to(TaskProject.objects.filter(user=user, workplace=workplace), form.viewer)
    options = {'': []}
    for tag in TaskTag.objects.filter(user=user, workplace=workplace, space__project__in=projects).values('pk', 'name', 'space__project_id'):
        options.setdefault(str(tag['space__project_id'] or ''), []).append({'id': str(tag['pk']), 'name': tag['name']})
    form.fields['tags'].widget.attrs.update({
        'data-tag-project-options': json.dumps(options),
        'data-tag-project': str(project.pk) if space else '',
    })
    return tags_in_scope(user, workplace, space)


def tag_action(request, space):
    """Return a response on success, or modal context for an invalid form."""
    from .forms import TaskTagForm
    action = request.POST.get('action')
    if space is None or action not in TAG_ACTIONS:
        raise Http404
    if not editable_to(TaskProject.objects.filter(pk=space.project_id), request.user).exists():
        raise PermissionDenied
    user, workplace = workspace_owner(request), request.workplace
    tags = tags_in_scope(user, workplace, space)
    url = request.path + '?view=tags'
    # Keep directory filters, but never accept a destination outside this directory.
    if request.GET.get('view') == 'tags':
        url = request.get_full_path()
    if action in {'create_tag', 'edit_tag'}:
        tag = get_object_or_404(tags, pk=_posted_pk(request, 'tag_id')) if action == 'edit_tag' else TaskTag(user=user, workplace=workplace, space=space)
        form = TaskTagForm(request.POST, instance=tag, user=user, workplace=workplace, space=space)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError:
                form.add_error('name', 'Taki tag już istnieje.')
            else:
                messages.success(request, 'Tag dodany.' if action == 'create_tag' else 'Tag zaktualizowany.')
                return redirect(url)
        return {'tag_form': form, 'tag_modal_open': True, 'tag_edit_mode': action == 'edit_tag', 'tag_edit_tag_id': tag.pk or ''}
    if action == 'delete_tag':
        ids = request.POST.getlist('tag_ids') or [request.POST.get('tag_id', '')]
        if not ids or any(not str(value).isdecimal() or len(str(value)) > 18 for value in ids):
            raise Http404
        ids = set(map(int, ids))
        with transaction.atomic():
            selected = tags.filter(pk__in=ids)
            if selected.count() != len(ids):
                raise Http404
            selected.delete()
        messages.success(request, 'Tag usunięty.' if len(ids) == 1 else f'Usunięto tagi ({len(ids)}).')
        return redirect(url)
    tag = get_object_or_404(tags, pk=_posted_pk(request, 'tag_id'))
    if action in {'add_tag_note', 'update_tag_notes'}:
        message = (request.POST.get('message') or request.POST.get('description') or '').strip()
        if message:
            TaskTagNote.objects.create(tag=tag, author=request.user, message=message)
            messages.success(request, 'Notatka dodana.')
        else:
            messages.error(request, 'Wpisz treść notatki.')
        return redirect(url)
    note = get_object_or_404(tag.tag_notes, pk=_posted_pk(request, 'note_id'), author=request.user)
    if action == 'delete_tag_note':
        note.delete()
        messages.success(request, 'Notatka usunięta.')
        return redirect(url)
    message = (request.POST.get('message') or '').strip()
    ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not message:
        if ajax:
            return JsonResponse({'status': 'error', 'message': 'Wpisz treść notatki.'}, status=400)
        messages.error(request, 'Wpisz treść notatki.')
        return redirect(url)
    note.message, note.edited_at = message, timezone.now()
    note.save(update_fields=['message', 'updated_at', 'edited_at'])
    if ajax:
        edited = timezone.localtime(note.edited_at)
        return JsonResponse({'status': 'success', 'message': 'Notatka zaktualizowana.', 'note': {
            'message': note.message, 'edited_at': edited.isoformat(), 'edited_at_label': edited.strftime('%d.%m.%Y, %H:%M'),
        }})
    messages.success(request, 'Notatka zaktualizowana.')
    return redirect(url)
