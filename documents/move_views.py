"""Shared, scoped moves for the two independent document catalogs."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .location_lock import location_write


class MoveForm(forms.Form):
    target = forms.ChoiceField(label='Przenieś do', widget=forms.Select(attrs={
        'class': 'form-select tasks-inline-select',
    }), error_messages={'invalid_choice': 'Wybierz dostępny folder lub dysk.'})

    def __init__(self, *args, choices, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target'].choices = choices


def _subtree(folders, root):
    children = {}
    for folder in folders.values():
        children.setdefault(folder.parent_id, []).append(folder.pk)
    found, pending = set(), [root]
    while pending:
        pk = pending.pop()
        if pk in found:
            continue
        found.add(pk)
        pending.extend(children.get(pk, []))
    return found


@login_required
@require_http_methods(['GET', 'POST'])
@location_write
def move(request, pk, kind='document', drive=False):
    from . import editor_views, views
    catalog = views if drive else editor_views
    scope_folders, documents = catalog._folders(request), catalog._documents(request)
    libraries = {item.pk: item for item in views._libraries(request)} if drive else {}
    if drive:
        scope_folders = scope_folders.filter(library_id__in=libraries)
        documents = documents.filter(library_id__in=libraries)
    folders = {item.pk: item for item in scope_folders}
    if kind == 'folder':
        item = folders.get(pk)
        if not item:
            raise Http404
        parent = folders.get(item.parent_id)
        subtree = _subtree(folders, pk)
    else:
        source = documents.select_for_update() if request.method == 'POST' else documents
        item = get_object_or_404(source, pk=pk, deleted_at__isnull=True)
        parent, subtree = folders.get(item.folder_id), set()
    parent_id = item.parent_id if kind == 'folder' else item.folder_id
    if parent_id and (parent is None or (drive and parent.library_id != item.library_id)):
        raise Http404
    source_library = libraries.get(item.library_id) if drive else None
    context = catalog._context(request, source_library, parent) if drive else catalog._context(request, parent)

    choices = [(f'library:{key}', library.name + ' (folder główny)') for key, library in libraries.items()] if drive else [('root', 'Dokumenty (folder główny)')]
    targets = {}
    for folder in folders.values():
        if folder.pk in subtree:
            continue
        path, seen, ancestor = [folder.name], {folder.pk}, folder
        while ancestor.parent_id:
            if ancestor.parent_id in seen:
                break
            seen.add(ancestor.parent_id)
            ancestor = folders.get(ancestor.parent_id)
            if not ancestor or (drive and ancestor.library_id != folder.library_id):
                break
            path.append(ancestor.name)
        else:
            if drive:
                path.append(libraries[folder.library_id].name)
            value = f'folder:{folder.pk}'
            targets[value] = folder
            choices.append((value, ' / '.join(reversed(path))))
    current = f'folder:{parent.pk}' if parent else (f'library:{source_library.pk}' if drive else 'root')
    form = MoveForm(request.POST if request.method == 'POST' else None, choices=choices, initial={'target': current})
    if request.POST.get('target') in {f'folder:{pk}' for pk in subtree}:
        form.fields['target'].error_messages['invalid_choice'] = 'Nie można przenieść folderu do niego samego ani do jego podfolderu.'
    if request.method == 'POST' and form.is_valid():
        value = form.cleaned_data['target']
        target = targets.get(value)
        library = libraries[target.library_id if target else int(value.split(':')[1])] if drive else None
        changed = value != current
        try:
            with transaction.atomic():
                if kind == 'folder':
                    if any(folder.pk != item.pk and folder.parent_id == (target.pk if target else None)
                           and folder.name.casefold() == item.name.casefold()
                           and (not drive or folder.library_id == library.pk) for folder in folders.values()):
                        raise forms.ValidationError('Folder o tej nazwie już istnieje w tym miejscu.')
                    if drive and library.pk != item.library_id:
                        # Never carry an inconsistent or foreign subtree into another drive.
                        folder_model, document_model = scope_folders.model, documents.model
                        if (folder_model.objects.filter(parent_id__in=subtree).exclude(pk__in=subtree).exists()
                                or scope_folders.filter(pk__in=subtree).exclude(library=source_library).exists()
                                or document_model.objects.filter(folder_id__in=subtree).exclude(pk__in=documents.filter(library=source_library)).exists()):
                            raise forms.ValidationError('Nie można przenieść folderu z niespójną zawartością.')
                        # Only location metadata changes; include trash to preserve its restore location.
                        scope_folders.filter(pk__in=subtree).exclude(pk=item.pk).update(library=library)
                        documents.filter(folder_id__in=subtree).update(library=library, updated_at=timezone.now(), revision=F('revision') + 1)
                        item.library = library
                    item.parent = target
                    if changed:
                        item.save(update_fields=['parent', 'library'] if drive else ['parent'])
                elif changed:
                    item.folder = target
                    item.revision += 1
                    fields = ['folder', 'revision', 'updated_at']
                    if drive:
                        item.library = library
                        fields.append('library')
                    item.save(update_fields=fields)
        except (IntegrityError, forms.ValidationError) as error:
            form.add_error('target', error if isinstance(error, forms.ValidationError) else 'Folder o tej nazwie już istnieje w tym miejscu.')
        else:
            message = 'Przeniesiono folder.' if kind == 'folder' else 'Przeniesiono plik.'
            if changed:
                messages.success(request, message)
            if request.headers.get('X-Document-Move') == 'true':
                return JsonResponse({'ok': True})
            return views._form_success(request, context['folder_url'])
    if request.headers.get('X-Document-Move') == 'true':
        return JsonResponse({'error': ' '.join(str(error) for errors in form.errors.values() for error in errors)}, status=400)
    context.update({'form': form, 'form_title': f'Przenieś: {item.name if kind == "folder" else item.title}', 'submit_label': 'Przenieś'})
    return views._render_form(request, context) if drive else editor_views._modal(request, context)
